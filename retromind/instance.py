"""Per-user local IPC for activation and graceful installer shutdown."""
import hashlib
import os
from pathlib import Path
from PySide6.QtGui import QWindow
from PySide6.QtNetwork import QLocalServer, QLocalSocket


def coordinate(app, root_getter, quit_for_update=False):
    name='RetroMindPlayer-5C759A24-'+hashlib.sha256((str(Path.home()).casefold()+os.environ.get('RETROMIND_TEST_INSTANCE_NAMESPACE','')).encode()).hexdigest()[:16]
    socket=QLocalSocket()
    socket.connectToServer(name)
    if socket.waitForConnected(500):
        socket.write(b'quit\n' if quit_for_update else b'activate\n')
        socket.waitForBytesWritten(1000)
        if quit_for_update:
            # Wait for orderly shutdown: bookmark, window state and worker draining.
            if socket.state()!=QLocalSocket.UnconnectedState and not socket.waitForDisconnected(30000):
                return None, 1
        else:
            socket.disconnectFromServer()
        return None, 0
    if quit_for_update:
        return None, 0
    server=QLocalServer(app)
    server.setSocketOptions(QLocalServer.UserAccessOption)
    if not server.listen(name):
        # A concurrent launch may have won the listener race. Do not open two players.
        return None, 1
    def connected():
        connection=server.nextPendingConnection()
        if connection is None:
            return
        def command():
            data=bytes(connection.readAll()).strip()
            root=root_getter()
            if data==b'quit':
                if root:
                    root.close()
                else:
                    app.quit()
            elif data==b'activate' and root:
                if root.visibility()==QWindow.Minimized:
                    root.showNormal()
                root.raise_(); root.requestActivate()
            # Keep quit socket open until application teardown confirms process exit.
            if data!=b'quit':
                connection.disconnectFromServer()
        connection.readyRead.connect(command)
        connection.disconnected.connect(connection.deleteLater)
        if connection.bytesAvailable():
            command()
    server.newConnection.connect(connected)
    return server, None
