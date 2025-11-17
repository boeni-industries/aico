import Cocoa
import FlutterMacOS
import WebKit

/// Platform channel plugin to enable transparent background for WKWebView on macOS
/// 
/// This plugin provides a method to set the drawsBackground property to false,
/// which is required for true transparency on macOS WKWebView.
/// 
/// Also automatically observes the view hierarchy to immediately set transparency
/// when WKWebViews are added, preventing white flashes during rebuilds.
public class TransparentWebViewPlugin: NSObject, FlutterPlugin {
    private var hierarchyObserver: NSKeyValueObservation?
    
    public static func register(with registrar: FlutterPluginRegistrar) {
        print("[TransparentWebViewPlugin] Registering plugin...")
        let channel = FlutterMethodChannel(
            name: "aico.dev/transparent_webview",
            binaryMessenger: registrar.messenger
        )
        let instance = TransparentWebViewPlugin()
        registrar.addMethodCallDelegate(instance, channel: channel)
        
        // Start observing view hierarchy for new WKWebViews
        instance.startObservingViewHierarchy()
        
        print("[TransparentWebViewPlugin] Plugin registered successfully")
    }
    
    /// Start observing the view hierarchy for new WKWebViews
    private func startObservingViewHierarchy() {
        // Poll for new WKWebViews every 100ms
        Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            self?.checkForNewWebViews()
        }
        print("[TransparentWebViewPlugin] Started observing view hierarchy")
    }
    
    /// Check for new WKWebViews and make them transparent immediately
    private func checkForNewWebViews() {
        guard let window = NSApplication.shared.windows.first else { return }
        var count = 0
        findAndSetTransparent(in: window.contentView, count: &count)
    }
    
    public func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
        switch call.method {
        case "setTransparentBackground":
            setTransparentBackground(result: result)
        default:
            result(FlutterMethodNotImplemented)
        }
    }
    
    /// Finds all WKWebView instances in the view hierarchy and sets them to transparent
    private func setTransparentBackground(result: @escaping FlutterResult) {
        DispatchQueue.main.async {
            // Get the main Flutter window
            guard let window = NSApplication.shared.windows.first else {
                result(FlutterError(code: "NO_WINDOW", message: "No window found", details: nil))
                return
            }
            
            // Find all WKWebView instances recursively
            var webViewsFound = 0
            self.findAndSetTransparent(in: window.contentView, count: &webViewsFound)
            
            if webViewsFound > 0 {
                result(["success": true, "webViewsModified": webViewsFound])
            } else {
                result(FlutterError(code: "NO_WEBVIEW", message: "No WKWebView found", details: nil))
            }
        }
    }
    
    /// Recursively searches for WKWebView instances and sets them to transparent
    /// Continuously enforces transparency to prevent resets during navigation
    private func findAndSetTransparent(in view: NSView?, count: inout Int) {
        guard let view = view else { return }
        
        // Check if this view is a WKWebView
        if let webView = view as? WKWebView {
            // Always enforce transparent background (don't track, just keep setting it)
            // This prevents any resets during navigation/rebuilds
            webView.setValue(false, forKey: "drawsBackground")
            count += 1
        }
        
        // Recursively check subviews
        for subview in view.subviews {
            findAndSetTransparent(in: subview, count: &count)
        }
    }
}
