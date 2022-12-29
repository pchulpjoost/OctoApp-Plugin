import logging
import signal
import sys
import random
import string

from octoprint_octoeverywhere.localauth import LocalAuth
from octoprint_octoeverywhere.snapshothelper import SnapshotHelper

from .octoeverywhereimpl import OctoEverywhere
from .octohttprequest import OctoHttpRequest
from .octopingpong import OctoPingPong
from .slipstream import Slipstream
from .sentry import Sentry
from .mdns import MDns
from .notificationshandler import NotificationsHandler
#from .threaddebug import ThreadDebug

#
# This file is used for development purposes. It can run the system outside of teh OctoPrint env.
#
# Use the following vars to configure the OctoEverywhere server address and the local OctoPrint address
# Use None if you don't want to overwrite the defaults.
#

# For local setups, use these vars to configure things.
LocalServerAddress = None
#LocalServerAddress = "127.0.0.1"

OctoPrintIp = None
OctoPrintIp = "192.168.1.12"

OctoPrintPort = None
OctoPrintPort = 80

# Define a printer id and private key
PrinterId = "0QVGBOO92TENVOVN9XW5T3KT6LV1XV8ODFUEQYWQ"
PrivateKey = "uduuitfqrsstnhhjpsxhmyqwvpxgnajqqbhxferoxunusjaybodfotkupjaecnccdxzwmeajqqmjftnhoonusnjatqcryxfvrzgibouexjflbrmurkhltmsd"

# Defines a place we can write files
PluginFilePathRoot = "C:\\Users\\quinn"

# A mock of the popup UI interface.
class UiPopupInvokerStub():
    def __init__(self, logger):
        self.Logger = logger

    def ShowUiPopup(self, title, text, msgType, autoHide):
        self.Logger.info("Client Notification Received. Title:"+title+"; Text:"+text+"; Type:"+msgType+"; AutoHide:"+str(autoHide))

# A mock of the popup UI interface.
NotificationHandlerInstance = None
class StatusChangeHandlerStub():
    def __init__(self, logger, printerId):
        self.Logger = logger
        self.PrinterId = printerId

    def OnPrimaryConnectionEstablished(self, octoKey, connectedAccounts):
        self.Logger.info("OnPrimaryConnectionEstablished - Connected Accounts:"+str(connectedAccounts) + " - OctoKey:"+str(octoKey))

        # Setup the notification handler
        NotificationHandlerInstance.SetOctoKey(octoKey)
        NotificationHandlerInstance.SetPrinterId(self.PrinterId)

        # Send a test notifications if desired.
        if LocalServerAddress is not None:
            NotificationHandlerInstance.SetServerProtocolAndDomain("http://"+LocalServerAddress)
            NotificationHandlerInstance.SetGadgetServerProtocolAndDomain("http://"+LocalServerAddress)
        #NotificationHandlerInstance.OnStarted("test.gcode")
        #handler.OnFailed("file name thats very long and too long for things.gcode", 20.2, "error")
        #handler.OnDone("filename.gcode", "304458605")
        #handler.OnPaused("filename.gcode")
        #handler.OnResume("filename.gcode")
        # NotificationHandlerInstance.OnError("test error string")
        # NotificationHandlerInstance.OnError("test error string")
        # NotificationHandlerInstance.OnError("test error string")
        #handler.OnZChange()
        #handler.OnZChange()
        #handler.OnFilamentChange()
        #handler.OnPrintProgress(20)

    def OnPluginUpdateRequired(self):
        self.Logger.info("On plugin update required message.")

def SignalHandler(sig, frame):
    print('Ctrl+C Pressed, Exiting!')
    sys.exit(0)

def GeneratePrinterId():
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(40))


if __name__ == '__main__':

    # Setup the logger.
    logger = logging.getLogger("octoeverywhere")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Init Sentry, but it won't report since we are in dev mode.
    Sentry.Init(logger, "dev", True)

    # Init the mdns client
    MDns.Init(logger, PluginFilePathRoot)
    #MDns.Get().Test()

    # This is a tool to help track stuck or leaked threads.
    #threadDebugger = ThreadDebug()
    #threadDebugger.Start(logger, 30)

    # Setup a signal handler to kill everything
    signal.signal(signal.SIGINT, SignalHandler)

    # Dev props
    printerId = GeneratePrinterId()
    OctoEverywhereWsUri = "wss://starport-v1.octoeverywhere.com/octoclientws"

    # Setup the http requester
    OctoHttpRequest.SetLocalHttpProxyPort(80)
    OctoHttpRequest.SetLocalHttpProxyIsHttps(False)
    OctoHttpRequest.SetLocalOctoPrintPort(5000)

    # Overwrite local dev props
    if OctoPrintIp is not None:
        OctoHttpRequest.SetLocalHostAddress(OctoPrintIp)
    if OctoPrintPort is not None:
        OctoHttpRequest.SetLocalOctoPrintPort(OctoPrintPort)
    if LocalServerAddress is not None:
        OctoEverywhereWsUri = "ws://"+LocalServerAddress+"/octoclientws"

    # Setup the local auth helper
    LocalAuth.Init(logger, None)
    LocalAuth.Get().SetApiKeyForTesting("SuperSecureApiKey")

    # Init the ping pong helper.
    OctoPingPong.Init(logger, PluginFilePathRoot, PrinterId)
    # If we are using a local dev connection, disable this or it will overwrite.
    if OctoEverywhereWsUri.startswith("ws://"):
        OctoPingPong.Get().DisablePrimaryOverride()

    # Setup the notification handler.
    NotificationHandlerInstance = NotificationsHandler(logger)

    # Setup the api command handler if needed for testing.
    # apiCommandHandler = ApiCommandHandler(logger, NotificationHandlerInstance, None)
    # Note this will throw an exception because we don't have a flask context setup.
    # result = apiCommandHandler.HandleApiCommand("status", None)

    # Setup the snapshot helper
    SnapshotHelper.Init(logger, None)

    # Init slipstream - This must be inited after localauth
    Slipstream.Init(logger)

    uiPopInvoker = UiPopupInvokerStub(logger)
    statusHandler = StatusChangeHandlerStub(logger, PrinterId)
    oe = OctoEverywhere(OctoEverywhereWsUri, PrinterId, PrivateKey, logger, uiPopInvoker, statusHandler, "1.10.20")
    oe.RunBlocking()
