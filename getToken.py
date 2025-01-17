from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import QUrl, pyqtSignal
from PyQt5.QtGui import QIcon
import sys
import re

ACCESS_TOKEN_REGEX = r'access_token=([^&]*)'

class CustomWebEnginePage(QWebEnginePage):
    token_found = pyqtSignal(str)

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceId):
        match = re.search(ACCESS_TOKEN_REGEX, message)
        if match:
            token = match.group(1)
            self.token_found.emit(token)


class TokenWindow(QMainWindow):
    def __init__(self, initial_url, icon_path=None):
        super().__init__()
        self.setWindowTitle("Authorization")
        self.setGeometry(100, 100, 700, 800)
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

        self.browser = QWebEngineView()
        self.page = CustomWebEnginePage(self.browser)
        self.browser.setPage(self.page)
        self.page.token_found.connect(self.on_token_found)
        self.browser.urlChanged.connect(self.on_url_changed)
        self.browser.page().profile().cookieStore().deleteAllCookies()
        self.browser.setUrl(QUrl(initial_url))

        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.browser)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.token = None

    def on_token_found(self, token):
        self.token = token
        QApplication.quit()

    def on_url_changed(self, url):
        url_str = url.toString()
        print(url_str)
        if "music" in url_str:
            self.browser.setUrl(QUrl("https://oauth.yandex.ru"))
        elif "oauth.yandex" in url_str:
            self.execute_fetch_script()

    def execute_fetch_script(self):
        script = """
        fetch("https://oauth.yandex.ru/authorize?response_type=token&client_id=23cabbbdc6cd418abb4b39c32c41195d")
            .then((response) => response.text())
            .then((text) => {
                const tokenMatch = text.match(/access_token=(.*?)&/);
                if (tokenMatch) {
                    console.log("access_token=" + tokenMatch[1]);
                }
            });
        """
        self.browser.page().runJavaScript(script)

def get_yandex_music_token(icon_path=None):
    app = QApplication(sys.argv)
    initial_url = "https://oauth.yandex.ru/authorize?response_type=token&client_id=23cabbbdc6cd418abb4b39c32c41195d" # Offical oauth url on Yandex.Music
    token_window = TokenWindow(initial_url, icon_path)
    token_window.show()
    app.exec_()
    return token_window.token