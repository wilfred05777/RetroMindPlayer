"""Targeted record transactions, queue independence and native QML menus."""
from pathlib import Path
import hashlib
import os
import sqlite3
import pytest
from PySide6.QtCore import QObject, QPoint, QPointF, Qt, QMetaObject, Q_ARG
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtCore import QUrl
from PySide6.QtTest import QTest
from retromind.controller import Controller
from retromind.repository import Repository
from retromind.queue_service import PlayQueue
from retromind.services import ImportService
from test_controller import fixture_audio, wait_until


@pytest.fixture
def library(tmp_path):
    for name in ('Alpha','Bravo','Charlie'):
        fixture_audio(tmp_path/(name+'.wav'))
    repo=Repository(tmp_path/'library.sqlite3')
    ImportService(repo).scan(tmp_path)
    ids=[track['id'] for track in repo.tracks()]
    a,b=repo.create_playlist('First playlist'),repo.create_playlist('Second playlist')
    for playlist in (a,b):
        for track in ids:
            repo.add_to_playlist(playlist,track)
    return repo,ids,a,b


def test_playlist_rename_delete_and_membership_persistence(library):
    repo,ids,a,b=library
    repo.favourite(ids[1]);repo.record_play(ids[1]);repo.save_setting('volume','.31')
    repo.rename_playlist(a,"O'Brien collection")
    with pytest.raises(ValueError): repo.rename_playlist(a,'   ')
    with pytest.raises(ValueError): repo.rename_playlist(a,'Second playlist')
    repo.remove_from_playlist(a,ids[1])
    assert [row['id'] for row in repo.tracks(playlist_id=a)]==[ids[0],ids[2]]
    assert [row['id'] for row in repo.tracks(playlist_id=b)]==ids
    assert repo.track(ids[1])['favourite']==1
    repo.save_setting('playlist',a);repo.save_setting('view','playlist')
    repo.delete_playlist(a)
    restored=Repository(repo.path)
    assert restored.playlist(a) is None and restored.playlist(b)
    assert len(restored.tracks())==3 and restored.setting('playlist')=='0'
    assert restored.setting('view')=='all' and restored.setting('volume')=='.31'
    assert restored.tracks(view='recently_played')[0]['id']==ids[1]
    for builtin in (0,-1):
        with pytest.raises(ValueError): restored.delete_playlist(builtin)
    with restored.connect() as db:
        assert db.execute('SELECT count(*) FROM playlist_tracks WHERE playlist_id=?',(a,)).fetchone()[0]==0


def test_library_removal_is_transactional_and_keeps_files(library):
    repo,ids,a,b=library
    target=ids[1]
    source=Path(repo.track(target)['path']);before=hashlib.sha256(source.read_bytes()).hexdigest()
    repo.record_play(target);repo.record_play(ids[0]);repo.favourite(target)
    repo.save_setting('last_track',target);repo.save_setting('last_position',1200);repo.save_setting('volume','.29')
    with repo.connect() as db:
        db.executescript("CREATE TRIGGER reject_removal BEFORE DELETE ON tracks BEGIN SELECT RAISE(ABORT,'test rollback'); END;")
    with pytest.raises(sqlite3.IntegrityError): repo.remove_track(target)
    assert repo.track(target) and len(repo.tracks(playlist_id=a))==3
    assert repo.setting('last_track')==str(target) and repo.tracks(view='recently_played')
    with repo.connect() as db: db.execute('DROP TRIGGER reject_removal')
    repo.remove_track(target)
    assert repo.track(target) is None
    for playlist in (a,b): assert [row['id'] for row in repo.tracks(playlist_id=playlist)]==[ids[0],ids[2]]
    assert repo.setting('last_track')=='' and repo.setting('last_position')==''
    assert repo.setting('volume')=='.29'
    with repo.connect() as db:
        assert not db.execute('SELECT * FROM history WHERE track_id=?',(target,)).fetchall()
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    assert ImportService(repo).import_paths([source])['added']==1


@pytest.mark.parametrize('direction,expected',[(1,3),(-1,1)])
def test_discard_current_queue_has_no_stale_cursor(direction,expected):
    queue=PlayQueue();queue.start([1,2,3],2);queue.discard(2)
    assert queue.current is None and queue.upcoming==[3]
    assert queue.advance(direction)==expected
    assert 2 not in queue.items and 2 not in queue.original
    queue.discard(expected)
    queue.repeat='all'
    assert queue.advance() in queue.items
    assert queue.append(9) and not queue.append(9)
    queue.set_shuffle(True);queue.set_shuffle(False)
    assert all(item in (1,3,9) for item in queue.items)


@pytest.fixture
def ui(app,library):
    repo,ids,a,b=library
    controller=Controller(repo);controller.setVolume(0);controller.navigate('all')
    engine=QQmlApplicationEngine();warnings=[]
    engine.warnings.connect(lambda values: warnings.extend(value.toString() for value in values))
    engine.rootContext().setContextProperty('controller',controller)
    engine.load(QUrl.fromLocalFile(str(Path('retromind/qml/Main.qml').resolve())))
    assert engine.rootObjects(),warnings
    root=engine.rootObjects()[0]
    screen=app.primaryScreen();available=screen.availableGeometry()
    root.setScreen(screen)
    root.setWidth(min(1440,available.width()));root.setHeight(max(600,min(900,available.height()-40)))
    root.setPosition(available.topLeft()+QPoint(0,min(0,available.height()-root.height()-40)))
    root.requestActivate();assert QTest.qWaitForWindowActive(root,3000)
    QTest.qWait(100)
    yield root,controller,repo,ids,a,b,warnings
    controller.shutdown();root.close();del engine;app.processEvents()
    assert not warnings,'\n'.join(warnings)


def find_item(root,name):
    item=root.findChild(QQuickItem,name)
    if item:
        return item
    pending=[root.contentItem()]
    while pending:
        item=pending.pop()
        if item.objectName()==name:
            return item
        pending.extend(item.childItems())
    return None


def click(root,item,button=Qt.LeftButton):
    assert item is not None
    name=item.objectName()
    # Virtualized rows can exist in the cache but be clipped. Scroll their model
    # entry into view before sending actual pointer events.
    ancestor=item.parentItem()
    while ancestor:
        if ancestor.metaObject().className() in ('QQuickListView','QQuickGridView'):
            model=ancestor.property('model') if name.rsplit('_',1)[-1].isdigit() else None
            if isinstance(model,list):
                target=int(name.rsplit('_',1)[-1])
                index=next((index for index,row in enumerate(model) if isinstance(row,dict) and row.get('id')==target),None)
                if index is not None:
                    QMetaObject.invokeMethod(ancestor,'positionViewAtIndex',Q_ARG(int,index),Q_ARG(int,4))
                    QTest.qWait(50)
                    item=find_item(root,name)
            break
        ancestor=ancestor.parentItem()
    point=item.mapToScene(QPointF(min(100,item.width()/2),item.height()/2))
    top=item.mapToScene(QPointF(0,0));bottom=item.mapToScene(QPointF(item.width(),item.height()))
    left,right=max(0,top.x()),min(root.width(),bottom.x())
    upper,lower=max(0,top.y()),min(root.height(),bottom.y())
    ancestor=item.parentItem()
    while ancestor:
        if ancestor.clip():
            top=ancestor.mapToScene(QPointF(0,0));bottom=ancestor.mapToScene(QPointF(ancestor.width(),ancestor.height()))
            left,right=max(left,top.x()),min(right,bottom.x())
            upper,lower=max(upper,top.y()),min(lower,bottom.y())
        ancestor=ancestor.parentItem()
    assert right>left and lower>upper, 'Target has no visible interaction area'
    point=QPointF(max(left+1,min(point.x(),right-1)),max(upper+1,min(point.y(),lower-1))).toPoint()
    QTest.mouseClick(root,button,pos=point)
    QTest.qWait(30)


def test_right_click_target_keyboard_grid_and_cancelled_confirmation(app,ui):
    root,c,repo,ids,a,b,warnings=ui
    root.setProperty('selectedTrack',ids[0])
    row=find_item(root,'mediaRow_'+str(ids[1]))
    menu=root.findChild(QObject,'mediaContextMenu')
    click(root,row,Qt.RightButton)
    wait_until(app,lambda: menu.property('opened'))
    assert menu.property('mediaId')==ids[1] and not c.playing
    assert c.playback.player.source().isEmpty()
    remove_playlist=find_item(root,'mediaRemovePlaylistAction')
    assert not remove_playlist.isVisible()
    click(root,find_item(root,'mediaFavouriteAction'))
    assert repo.track(ids[1])['favourite']==1 and repo.track(ids[0])['favourite']==0
    row=find_item(root,'mediaRow_'+str(ids[2]));row.forceActiveFocus(Qt.TabFocusReason)
    QTest.keyClick(root,Qt.Key_F10,Qt.ShiftModifier)
    wait_until(app,lambda: menu.property('opened'))
    assert menu.property('mediaId')==ids[2] and not c.playing
    QTest.keyClick(root,Qt.Key_Escape);wait_until(app,lambda: not menu.property('opened'))
    c.togglePanel('grid');app.processEvents();QTest.qWait(100)
    card=find_item(root,'mediaCard_'+str(ids[2]))
    assert card
    click(root,card,Qt.RightButton)
    wait_until(app,lambda: menu.property('opened'))
    assert menu.property('mediaId')==ids[2] and not c.playing
    click(root,find_item(root,'mediaRemoveLibraryAction'))
    confirmation=root.findChild(QObject,'removalConfirmation')
    wait_until(app,lambda: confirmation.property('opened'))
    assert c.pendingRemoval['id']==ids[2]
    assert 'Charlie' in root.findChild(QObject,'removalExplanation').property('text')
    QTest.keyClick(root,Qt.Key_Escape)
    wait_until(app,lambda: not confirmation.property('opened'))
    assert not c.pendingRemoval and len(repo.tracks())==3
    assert not c.confirmRemoval()
    c.navigate('all');c.requestDeletePlaylist(0)
    assert not c.pendingRemoval and len(repo.playlists())==2


def test_sidebar_rename_and_playlist_delete_do_not_stop_queue(app,ui):
    root,c,repo,ids,a,b,warnings=ui
    c.selectPlaylist(a);app.processEvents()
    sidebar=find_item(root,'sidebarPlaylist_'+str(b))
    click(root,sidebar,Qt.RightButton)
    menu=root.findChild(QObject,'playlistContextMenu')
    wait_until(app,lambda: menu.property('opened'))
    assert menu.property('playlistId')==b and c.selectedPlaylist==a and not c.playing
    click(root,find_item(root,'playlistRenameAction'))
    field=find_item(root,'playlistNameInput')
    assert field.property('text')=='Second playlist'
    field.setProperty('text',"Renamed \u97f3\u4e50")
    QTest.keyClick(root,Qt.Key_Return);app.processEvents()
    assert Repository(repo.path).playlist(b)['name']=="Renamed \u97f3\u4e50"
    c.playPlaylist(b);wait_until(app,lambda: c.playing)
    active=c.currentTrack['id'];queue=c.queue.items.copy();source=c.playback.player.source()
    c.removeFromPlaylistAt(active,b)
    assert c.playing and c.queue.items==queue and c.repo.track(active)
    c.selectPlaylist(b);c.requestDeletePlaylist(b)
    confirmation=root.findChild(QObject,'removalConfirmation')
    wait_until(app,lambda: confirmation.property('opened'))
    click(root,find_item(root,'confirmRemovalButton'))
    wait_until(app,lambda: not confirmation.property('opened'))
    assert not repo.playlist(b) and c.view=='all' and c.selectedPlaylist==0
    assert c.playing and c.currentTrack['id']==active and c.playback.player.source()==source
    assert c.queue.items==queue
    assert len(repo.tracks())==3 and len(repo.tracks(playlist_id=a))==3


def test_library_current_and_queued_deletion_navigation_and_explorer(app,ui,monkeypatch):
    root,c,repo,ids,a,b,warnings=ui
    from retromind import shell
    revealed=[];monkeypatch.setattr(shell,'reveal_file',lambda path: revealed.append(path))
    c.showInExplorer(ids[1]);assert revealed==[repo.track(ids[1])['path']]
    c.playTrack(ids[1]);wait_until(app,lambda: c.playing)
    path=Path(c.currentTrack['path']);before=path.read_bytes()
    root.setProperty('selectedTrack',ids[1])
    c.requestRemoveLibrary(ids[1]);assert c.confirmRemoval()
    assert not c.playing and not c.currentTrack and c.playback.player.source().isEmpty()
    assert root.property('selectedTrack') == -1
    assert ids[1] not in c.queue.items and ids[1] not in c.queue.original
    assert path.read_bytes()==before
    from PySide6.QtMultimedia import QMediaPlayer
    c.on_media_status(QMediaPlayer.EndOfMedia)
    assert not c.playing and not c.currentTrack  # Ignore stale end signals after removal.
    c.step(1);wait_until(app,lambda: c.playing)
    assert c.currentTrack['id']==ids[2]
    c.requestRemoveLibrary(ids[0]);assert c.confirmRemoval()
    assert c.playing and c.currentTrack['id']==ids[2]
    c.toggleShuffle();c.cycleRepeat();c.step(-1)
    assert set(c.queue.items)=={ids[2]} and c.queue.current==ids[2]
    c.requestRemoveLibrary(ids[2]);assert c.confirmRemoval()
    assert not c.queue.items and not c.currentTrack
    c.step(1);c.step(-1);c.togglePlay()
    assert not c.playing

def test_media_menu_submenu_queue_details_and_window_bounds(app,ui):
    root,c,repo,ids,a,b,warnings=ui
    repo.remove_from_playlist(a,ids[1]);c.refresh()
    root.setWidth(800);root.setHeight(600);QTest.qWait(100)
    row=find_item(root,'mediaRow_'+str(ids[1]))
    menu=root.findChild(QObject,'mediaContextMenu')
    click(root,row,Qt.RightButton);wait_until(app,lambda: menu.property('opened'))
    content=menu.property('contentItem')
    scene=content.mapToScene(QPointF(0,0))
    assert scene.x()>=0 and scene.y()>=0
    assert scene.x()+content.width()<=root.width()
    assert scene.y()+content.height()<=root.height()
    folder=os.environ.get('RETROMIND_MENUS_QA')
    if folder:
        Path(folder).mkdir(parents=True,exist_ok=True)
        root.grabWindow().save(str(Path(folder)/'media-menu-800.png'))
    # Navigate actual menu focus, then enter the real submenu.
    for _ in range(12):
        if menu.property('currentIndex')==2:
            break
        QTest.keyClick(root,Qt.Key_Down)
    assert menu.property('currentIndex')==2
    QTest.keyClick(root,Qt.Key_Right)
    choices=root.findChild(QObject,'playlistChoicesMenu')
    wait_until(app,lambda: choices.property('opened'))
    if choices.property('currentIndex') < 0:
        QTest.keyClick(root,Qt.Key_Down)
    QTest.keyClick(root,Qt.Key_Return);QTest.qWait(50)
    assert any(row['id']==ids[1] for row in repo.tracks(playlist_id=a))
    assert not c.playing
    row=find_item(root,'mediaRow_'+str(ids[1]))
    click(root,row,Qt.RightButton);wait_until(app,lambda: menu.property('opened'))
    click(root,find_item(root,'mediaQueueAction'))
    assert c.queue.upcoming==[ids[1]] and not c.playing
    click(root,find_item(root,'mediaRow_'+str(ids[1])),Qt.RightButton)
    wait_until(app,lambda: menu.property('opened'))
    assert not find_item(root,'mediaQueueAction').isVisible()
    click(root,find_item(root,'mediaDetailsAction'))
    details=root.findChild(QObject,'mediaDetailsDialog')
    wait_until(app,lambda: details.property('opened'))
    assert details.property('media')['id']==ids[1]
    QTest.keyClick(root,Qt.Key_Escape)
    c.togglePlay();wait_until(app,lambda:c.playing)
    assert c.currentTrack['id']==ids[1]


def test_empty_playlists_and_queue_state_after_deletions(app,ui):
    root,c,repo,ids,a,b,warnings=ui
    empty=repo.create_playlist('Empty');c.refresh()
    c.playPlaylist(empty);assert not c.playing and 'empty' in c.status
    c.selectPlaylist(empty);app.processEvents();QTest.qWait(30)
    button=find_item(root,'playlistHeadingMenu')
    assert button.isVisible()
    click(root,button)
    menu=root.findChild(QObject,'playlistContextMenu')
    wait_until(app,lambda: menu.property('opened'))
    assert not find_item(root,'playlistPlayAction').isEnabled()
    QTest.keyClick(root,Qt.Key_Escape)
    c.requestDeletePlaylist(empty);c.cancelRemoval()
    assert not c.confirmRemoval() and repo.playlist(empty)
    c.addToQueue(ids[0]);c.addToQueue(ids[2]);c.toggleShuffle();c.toggleShuffle()
    assert c.queue.upcoming==[ids[0],ids[2]]
    c.requestRemoveLibrary(ids[2]);assert c.confirmRemoval()
    assert c.queue.upcoming==[ids[0]]
    prior=c.queue.items.copy();c.playTrack(ids[2]);assert c.queue.items==prior and not c.playing

def test_ellipsis_keyboard_buttons_open_without_playing(app,ui):
    root,c,repo,ids,a,b,warnings=ui
    c.selectPlaylist(a);app.processEvents();QTest.qWait(50)
    sidebar=find_item(root,'sidebarPlaylist_'+str(b))
    sidebar.forceActiveFocus(Qt.TabFocusReason);app.processEvents()
    more=find_item(root,'playlistMore_'+str(b))
    assert more.isVisible()
    more.forceActiveFocus(Qt.TabFocusReason)
    QTest.keyClick(root,Qt.Key_Return)
    playlist_menu=root.findChild(QObject,'playlistContextMenu')
    wait_until(app,lambda:playlist_menu.property('opened'))
    assert playlist_menu.property('playlistId')==b and not c.playing
    QTest.keyClick(root,Qt.Key_Escape)
    wait_until(app,lambda:not playlist_menu.property('visible'))
    more=find_item(root,'mediaMore_'+str(ids[1]))
    more.forceActiveFocus(Qt.TabFocusReason)
    app.processEvents()
    assert more.hasActiveFocus()
    assert not root.findChild(QObject,'playbackSpaceShortcut').property('enabled')
    QTest.keyClick(root,Qt.Key_Space)
    media_menu=root.findChild(QObject,'mediaContextMenu')
    wait_until(app,lambda:media_menu.property('opened'))
    assert media_menu.property('mediaId')==ids[1] and not c.playing
    QTest.keyClick(root,Qt.Key_Escape)
    c.togglePanel('grid');app.processEvents();QTest.qWait(50)
    more=find_item(root,'cardMore_'+str(ids[1]))
    click(root,more)
    wait_until(app,lambda:media_menu.property('opened'))
    assert media_menu.property('mediaId')==ids[1] and not c.playing
    QTest.keyClick(root,Qt.Key_Escape)

def test_video_library_removal_exits_fullscreen_and_clears_frame(app,ui,tmp_path):
    from media_fixtures import make_video
    root,c,repo,ids,a,b,warnings=ui
    video=make_video(tmp_path/'playing-video.mp4')
    original=hashlib.sha256(video.read_bytes()).hexdigest()
    ImportService(repo).import_paths([video]);c.refresh()
    track=next(row for row in repo.tracks() if row['media_type']=='video')
    c.playTrack(track['id'])
    sink=c.playback.player.videoSink()
    wait_until(app,lambda:c.playing and c.hasVideo and sink.videoFrame().isValid())
    c.toggleFullscreen();wait_until(app,lambda:c.fullscreen)
    c.requestRemoveLibrary(track['id']);assert c.confirmRemoval()
    wait_until(app,lambda:not c.fullscreen and not sink.videoFrame().isValid())
    assert not c.playing and not c.currentTrack and c.playback.player.source().isEmpty()
    assert hashlib.sha256(video.read_bytes()).hexdigest()==original


def test_no_playlist_submenu_and_unavailable_file_actions(app,ui,tmp_path):
    root,c,repo,ids,a,b,warnings=ui
    for playlist in (a,b):repo.delete_playlist(playlist)
    repo.add_track(dict(path=str(tmp_path/'not-present.mp4'),title='Missing',media_type='video'))
    c.refresh();app.processEvents();QTest.qWait(50)
    missing=next(row for row in repo.tracks() if row['title']=='Missing')
    row=find_item(root,'mediaRow_'+str(missing['id']))
    click(root,row,Qt.RightButton)
    menu=root.findChild(QObject,'mediaContextMenu')
    wait_until(app,lambda:menu.property('opened'))
    assert not menu.property('hasPlaylistMenu')
    for name in ('mediaPlayAction','mediaQueueAction','mediaExplorerAction','mediaRemovePlaylistAction'):
        action=find_item(root,name)
        assert not action.isVisible() and action.property('implicitHeight')==0
    assert find_item(root,'mediaDetailsAction').isVisible()
    assert find_item(root,'mediaRemoveLibraryAction').isVisible()
    QTest.keyClick(root,Qt.Key_Escape)
