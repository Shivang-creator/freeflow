import AppKit
import Foundation

// MARK: - Animated Siri/FreeFlow Glowing Orb View
class GlowingOrbView: NSView {
    private let gradientLayer = CAGradientLayer()
    private let glowLayer = CALayer()
    private let pulseLayer = CALayer()
    
    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        wantsLayer = true
        setupLayers()
    }
    
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
    private func setupLayers() {
        guard let layer = self.layer else { return }
        
        // Outer glow
        glowLayer.frame = bounds.insetBy(dx: -4, dy: -4)
        glowLayer.cornerRadius = glowLayer.bounds.width / 2
        glowLayer.backgroundColor = NSColor(red: 0.0, green: 0.85, blue: 1.0, alpha: 0.35).cgColor
        glowLayer.shadowColor = NSColor(red: 0.0, green: 0.9, blue: 1.0, alpha: 1.0).cgColor
        glowLayer.shadowOpacity = 0.9
        glowLayer.shadowRadius = 14
        glowLayer.shadowOffset = .zero
        layer.addSublayer(glowLayer)
        
        // Pulse ring
        pulseLayer.frame = bounds
        pulseLayer.cornerRadius = bounds.width / 2
        pulseLayer.borderWidth = 1.5
        pulseLayer.borderColor = NSColor(red: 0.0, green: 0.85, blue: 1.0, alpha: 0.5).cgColor
        layer.addSublayer(pulseLayer)
        
        // Dynamic Radial Gradient Orb
        gradientLayer.frame = bounds
        gradientLayer.cornerRadius = bounds.width / 2
        gradientLayer.type = .radial
        gradientLayer.colors = [
            NSColor(red: 0.0, green: 0.95, blue: 0.8, alpha: 1.0).cgColor,
            NSColor(red: 0.0, green: 0.5, blue: 1.0, alpha: 0.9).cgColor,
            NSColor(red: 0.1, green: 0.1, blue: 0.9, alpha: 0.75).cgColor
        ]
        gradientLayer.startPoint = CGPoint(x: 0.5, y: 0.5)
        gradientLayer.endPoint = CGPoint(x: 1.0, y: 1.0)
        layer.addSublayer(gradientLayer)
        
        startBreathingAnimation()
    }
    
    func startBreathingAnimation() {
        // Breathing scale
        let scaleAnim = CABasicAnimation(keyPath: "transform.scale")
        scaleAnim.fromValue = 0.92
        scaleAnim.toValue = 1.08
        scaleAnim.duration = 1.3
        scaleAnim.autoreverses = true
        scaleAnim.repeatCount = .infinity
        scaleAnim.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        gradientLayer.add(scaleAnim, forKey: "orbPulse")
        
        // Glow pulse
        let glowAnim = CABasicAnimation(keyPath: "shadowRadius")
        glowAnim.fromValue = 8.0
        glowAnim.toValue = 18.0
        glowAnim.duration = 1.3
        glowAnim.autoreverses = true
        glowAnim.repeatCount = .infinity
        glowAnim.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
        glowLayer.add(glowAnim, forKey: "glowPulse")
    }
    
    func setState(state: String) {
        CATransaction.begin()
        CATransaction.setAnimationDuration(0.25)
        switch state {
        case "listening":
            gradientLayer.colors = [
                NSColor(red: 0.0, green: 1.0, blue: 0.75, alpha: 1.0).cgColor,
                NSColor(red: 0.0, green: 0.65, blue: 1.0, alpha: 0.9).cgColor,
                NSColor(red: 0.1, green: 0.2, blue: 0.85, alpha: 0.7).cgColor
            ]
            glowLayer.shadowColor = NSColor.cyan.cgColor
            pulseLayer.borderColor = NSColor(red: 0.0, green: 1.0, blue: 0.8, alpha: 0.6).cgColor
        case "thinking", "transcribing":
            gradientLayer.colors = [
                NSColor(red: 0.75, green: 0.2, blue: 1.0, alpha: 1.0).cgColor,
                NSColor(red: 0.35, green: 0.0, blue: 0.95, alpha: 0.9).cgColor,
                NSColor(red: 0.95, green: 0.25, blue: 0.6, alpha: 0.8).cgColor
            ]
            glowLayer.shadowColor = NSColor.magenta.cgColor
            pulseLayer.borderColor = NSColor(red: 0.8, green: 0.3, blue: 1.0, alpha: 0.6).cgColor
        case "speaking", "done", "injected":
            gradientLayer.colors = [
                NSColor(red: 0.0, green: 0.9, blue: 1.0, alpha: 1.0).cgColor,
                NSColor(red: 0.0, green: 0.5, blue: 1.0, alpha: 0.9).cgColor,
                NSColor(red: 0.0, green: 1.0, blue: 0.6, alpha: 0.7).cgColor
            ]
            glowLayer.shadowColor = NSColor(red: 0.0, green: 0.9, blue: 1.0, alpha: 1.0).cgColor
            pulseLayer.borderColor = NSColor(red: 0.0, green: 0.85, blue: 1.0, alpha: 0.6).cgColor
        default:
            break
        }
        CATransaction.commit()
    }
}

// MARK: - Animated Audio Waveform Bars
class AudioWaveformView: NSView {
    private var bars: [CALayer] = []
    
    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        wantsLayer = true
        setupBars()
    }
    
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
    private func setupBars() {
        guard let layer = self.layer else { return }
        let count = 4
        let barWidth: CGFloat = 3.5
        let spacing: CGFloat = 4.0
        let totalWidth = CGFloat(count) * barWidth + CGFloat(count - 1) * spacing
        let startX = (bounds.width - totalWidth) / 2
        
        for i in 0..<count {
            let bar = CALayer()
            let x = startX + CGFloat(i) * (barWidth + spacing)
            bar.frame = CGRect(x: x, y: (bounds.height - 12) / 2, width: barWidth, height: 12)
            bar.cornerRadius = 1.75
            bar.backgroundColor = NSColor(red: 0.0, green: 0.9, blue: 1.0, alpha: 0.85).cgColor
            layer.addSublayer(bar)
            bars.append(bar)
            
            // Staggered bounce animation
            let anim = CABasicAnimation(keyPath: "bounds.size.height")
            anim.fromValue = 5.0
            anim.toValue = 22.0
            anim.duration = 0.42 + Double(i) * 0.11
            anim.autoreverses = true
            anim.repeatCount = .infinity
            anim.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
            bar.add(anim, forKey: "waveAnim")
        }
    }
    
    func setActive(_ active: Bool) {
        for bar in bars {
            bar.opacity = active ? 0.95 : 0.2
        }
    }
}

// MARK: - Floating Pill HUD Window
class FreeFlowHUDController: NSObject {
    private var window: NSWindow!
    private var visualEffectView: NSVisualEffectView!
    private var orbView: GlowingOrbView!
    private var titleLabel: NSTextField!
    private var subtitleLabel: NSTextField!
    private var waveformView: AudioWaveformView!
    private var isVisible = false
    private var hideTimer: Timer?
    
    override init() {
        super.init()
        setupWindow()
    }
    
    private func setupWindow() {
        let width: CGFloat = 440
        let height: CGFloat = 68
        
        guard let screen = NSScreen.main else { return }
        let screenRect = screen.visibleFrame
        let x = screenRect.origin.x + (screenRect.width - width) / 2
        let y = screenRect.origin.y + screenRect.height - height - 12
        
        let frame = NSRect(x: x, y: y, width: width, height: height)
        window = NSWindow(contentRect: frame,
                          styleMask: [.borderless, .fullSizeContentView],
                          backing: .buffered,
                          defer: false)
        
        window.isOpaque = false
        window.backgroundColor = .clear
        window.level = .floating
        window.collectionBehavior = [.canJoinAllSpaces, .stationary, .ignoresCycle]
        window.ignoresMouseEvents = true
        window.alphaValue = 0.0
        
        // Frosted Glass Effect
        visualEffectView = NSVisualEffectView(frame: NSRect(x: 0, y: 0, width: width, height: height))
        visualEffectView.material = .hudWindow
        visualEffectView.blendingMode = .behindWindow
        visualEffectView.state = .active
        visualEffectView.wantsLayer = true
        visualEffectView.layer?.cornerRadius = 34
        visualEffectView.layer?.masksToBounds = true
        
        // Neon Ambient Border
        visualEffectView.layer?.borderWidth = 1.2
        visualEffectView.layer?.borderColor = NSColor(red: 0.0, green: 0.85, blue: 1.0, alpha: 0.45).cgColor
        visualEffectView.layer?.shadowColor = NSColor(red: 0.0, green: 0.85, blue: 1.0, alpha: 0.8).cgColor
        visualEffectView.layer?.shadowOpacity = 0.6
        visualEffectView.layer?.shadowRadius = 14
        visualEffectView.layer?.shadowOffset = .zero
        
        // Glowing Orb (Left)
        orbView = GlowingOrbView(frame: NSRect(x: 16, y: 16, width: 36, height: 36))
        visualEffectView.addSubview(orbView)
        
        // Title Label
        titleLabel = NSTextField(labelWithString: "FreeFlow")
        titleLabel.frame = NSRect(x: 64, y: 36, width: 310, height: 20)
        titleLabel.font = NSFont.systemFont(ofSize: 13, weight: .bold)
        titleLabel.textColor = NSColor(red: 0.0, green: 0.9, blue: 1.0, alpha: 1.0)
        visualEffectView.addSubview(titleLabel)
        
        // Subtitle / Response Label
        subtitleLabel = NSTextField(labelWithString: "Listening...")
        subtitleLabel.frame = NSRect(x: 64, y: 14, width: 310, height: 18)
        subtitleLabel.font = NSFont.systemFont(ofSize: 12, weight: .medium)
        subtitleLabel.textColor = NSColor(white: 0.92, alpha: 1.0)
        subtitleLabel.lineBreakMode = .byTruncatingTail
        visualEffectView.addSubview(subtitleLabel)
        
        // Waveform Bars (Right)
        waveformView = AudioWaveformView(frame: NSRect(x: 380, y: 19, width: 44, height: 30))
        visualEffectView.addSubview(waveformView)
        
        window.contentView = visualEffectView
    }
    
    func show(state: String = "listening", title: String = "FreeFlow", text: String = "Listening...", autoHideDelay: Double? = nil) {
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            self.hideTimer?.invalidate()
            self.hideTimer = nil
            
            self.titleLabel.stringValue = title.isEmpty ? "FreeFlow" : title
            self.subtitleLabel.stringValue = text
            self.orbView.setState(state: state)
            self.waveformView.setActive(state == "listening" || state == "speaking")
            
            if !self.isVisible {
                self.window.orderFront(nil)
                NSAnimationContext.runAnimationGroup { context in
                    context.duration = 0.22
                    context.timingFunction = CAMediaTimingFunction(name: .easeOut)
                    self.window.animator().alphaValue = 1.0
                }
                self.isVisible = true
            }
            
            if let delay = autoHideDelay {
                self.hideTimer = Timer.scheduledTimer(withTimeInterval: delay, repeats: false) { [weak self] _ in
                    self?.hide()
                }
            }
        }
    }
    
    func hide() {
        DispatchQueue.main.async { [weak self] in
            guard let self = self, self.isVisible else { return }
            self.hideTimer?.invalidate()
            self.hideTimer = nil
            
            NSAnimationContext.runAnimationGroup({ context in
                context.duration = 0.25
                context.timingFunction = CAMediaTimingFunction(name: .easeIn)
                self.window.animator().alphaValue = 0.0
            }, completionHandler: {
                self.window.orderOut(nil)
                self.isVisible = false
            })
        }
    }
}

// MARK: - Unix Domain Socket IPC Server
class HUDServer {
    private let primarySocketPath = "/tmp/freeflow_hud.sock"
    private let legacySocketPath = "/tmp/jarvis_hud.sock"
    private var serverSource: DispatchSourceRead?
    private var serverFd: Int32 = -1
    private let hud: FreeFlowHUDController
    
    init(hud: FreeFlowHUDController) {
        self.hud = hud
    }
    
    func start() {
        unlink(primarySocketPath)
        unlink(legacySocketPath)
        
        serverFd = socket(AF_UNIX, SOCK_STREAM, 0)
        guard serverFd >= 0 else {
            fputs("Failed to create socket\n", stderr)
            return
        }
        
        var addr = sockaddr_un()
        addr.sun_family = sa_family_t(AF_UNIX)
        
        let pathBytes = primarySocketPath.utf8CString
        withUnsafeMutablePointer(to: &addr.sun_path.0) { ptr in
            _ = pathBytes.withUnsafeBufferPointer { buf in
                memcpy(ptr, buf.baseAddress!, min(buf.count, 104))
            }
        }
        
        let size = socklen_t(MemoryLayout<sockaddr_un>.size)
        var bindAddr = addr
        let bindResult = withUnsafePointer(to: &bindAddr) { ptr in
            ptr.withMemoryRebound(to: sockaddr.self, capacity: 1) { saPtr in
                bind(serverFd, saPtr, size)
            }
        }
        
        guard bindResult == 0 else {
            fputs("Failed to bind socket at \(primarySocketPath)\n", stderr)
            close(serverFd)
            return
        }
        
        chmod(primarySocketPath, 0o777)
        // Also symlink to legacy socket for backward compatibility
        _ = symlink(primarySocketPath, legacySocketPath)
        listen(serverFd, 5)
        
        // Asynchronous socket accept queue
        let queue = DispatchQueue(label: "com.freeflow.hud.server")
        serverSource = DispatchSource.makeReadSource(fileDescriptor: serverFd, queue: queue)
        serverSource?.setEventHandler { [weak self] in
            guard let self = self else { return }
            var clientAddr = sockaddr_un()
            var clientLen = socklen_t(MemoryLayout<sockaddr_un>.size)
            let clientFd = withUnsafeMutablePointer(to: &clientAddr) { ptr in
                ptr.withMemoryRebound(to: sockaddr.self, capacity: 1) { saPtr in
                    accept(self.serverFd, saPtr, &clientLen)
                }
            }
            
            if clientFd >= 0 {
                self.handleClient(fd: clientFd)
            }
        }
        serverSource?.resume()
        print("⚡ FreeFlow Floating Pill HUD Server active on \(primarySocketPath)")
    }
    
    private func handleClient(fd: Int32) {
        let clientSource = DispatchSource.makeReadSource(fileDescriptor: fd, queue: DispatchQueue.global(qos: .userInteractive))
        clientSource.setEventHandler { [weak self] in
            var buffer = [UInt8](repeating: 0, count: 4096)
            let bytesRead = read(fd, &buffer, buffer.count)
            if bytesRead > 0 {
                let data = Data(bytes: buffer, count: bytesRead)
                if let str = String(data: data, encoding: .utf8) {
                    for line in str.components(separatedBy: "\n") {
                        let trimmed = line.trimmingCharacters(in: .whitespacesAndNewlines)
                        if !trimmed.isEmpty {
                            self?.processCommand(trimmed)
                        }
                    }
                }
            } else {
                clientSource.cancel()
                close(fd)
            }
        }
        clientSource.resume()
    }
    
    private func processCommand(_ jsonStr: String) {
        guard let data = jsonStr.data(using: .utf8),
              let dict = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return
        }
        
        let state = dict["state"] as? String ?? "listening"
        let title = dict["title"] as? String ?? "FreeFlow"
        let text = dict["text"] as? String ?? ""
        let autoHide = dict["auto_hide"] as? Double
        
        if state == "hide" {
            hud.hide()
        } else {
            hud.show(state: state, title: title, text: text, autoHideDelay: autoHide)
        }
    }
}

// MARK: - App Entry Point
let app = NSApplication.shared
app.setActivationPolicy(.accessory) // Headless floating window, no dock icon

let hudController = FreeFlowHUDController()
let server = HUDServer(hud: hudController)
server.start()

app.run()
