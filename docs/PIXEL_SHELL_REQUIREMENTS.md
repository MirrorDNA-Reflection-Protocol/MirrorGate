# Pixel "Mirror Shell" Implementation Requirements (v1.1)
**Target Device**: Pixel 9 Pro XL (GrapheneOS)
**Role**: Node A (Somatic Edge)
**Status**: Canonical Tech Spec

## 1. System Context (GrapheneOS Specifics)
Running on GrapheneOS affords us higher privacy control but imposes stricter permission handling.
- **Sandboxed Play Services**: Do NOT rely on proprietary Google APIs (e.g., Google Fused Location, unmodified ml-kit) if open alternatives exist.
- **Network Permission**: By default, GrapheneOS allows restricting network usage. The app must handle "No Network" gracefullly (fallback to local buffer).
- **Sensors**: Permission indicators are system-level strict. The "Mirror Active" overlay is redundant for privacy (GrapheneOS already shows green dots) but **mandatory for Agency attribution** (User must know *Mirror* is the one acting).

## 2. Core Architecture: "The Somatic Loop"

### A. Communication Layer ("The Nerve")
We cannot rely on file sync (Syncthing) for real-time actuation.
*   **Primary**: **Secure WebSocket (WSS)** over Local LAN.
    *   Mac Mini = Server (e.g., `wss://192.168.x.x:8888`).
    *   Pixel = Client.
    *   Auth: TLS + Ed25519 Challenge-Response using the Pulse Device Key.
*   **Secondary (Fallback)**: File Watcher (Syncthing shared folder) for high-latency instructions (journaling, configs).

### B. Execution Engine ("The Hand")
*   **Accessibility Service**: The core driver.
    *   Must declare `indefinite` capability to observing windows.
    *   **Action Primitive**: `performGesture` (Path-based taps/swipes).
*   **Digital Assistant Role**:
    *   Register as `android.service.voice.VoiceInteractionService` (optional but recommended for overlay priority).
    *   Allows "Wake on Phrase" (future expansion) and overlaying lockscreen (if configured).

### C. Inference Engine ("The Small Brain") — Future Ready
*   **Goal**: Prepare the shell to run `Llama-3-8B-Quantized` or `Phi-4` locally.
*   **Requirement**:
    *   Include bindings for `llama.cpp` (via JNI/CMake).
    *   Expose an `InferenceInterface` in the code:
        ```kotlin
        interface LocalBrain {
            fun decide(screenXml: String, goal: String): Action
        }
        ```
    *   *Phase 1 Implementation*: This interface returns "Null/remote" (sends XML to Mac).
    *   *Phase 2 Implementation*: Returns local actions for sub-100ms UI navigation.

## 3. Pulse Token Integration (Strict)
*   **Crypto**: **Sodium / BouncyCastle**.
*   **Token Format**: JSON (from Pulse Mac).
*   **Enforcement**:
    *   `onAccessibilityEvent`: Check `Pulse.isTokenValid()`.
    *   If `False`: Drop event, do nothing.
    *   If `True`: Log event to local ring-buffer, allow processing.

## 4. UI / UX Requirements
*   **The "Halo"**: A subtle, non-intrusive overlay border or "Dynamic Island" style pill when Pulse is active.
    *   *Color Code*: 
        *   Cyan (Breathing): Observing / Thinking.
        *   Amber (Solid): Navigating / Acting.
        *   Red (Pulsing): Critical / Requesting Confirmation.
*   **Kill Switch**:
    *   A notification shade entry "STOP MIRROR" (High Priority).
    *   Volume Up + Down hold (3s) = Emergency Shutdown (GrapheneOS friendly hardware key intercept).

## 5. Development Roadmap
1.  **Skeleton**: Generic Android Project, Kotlin, MinSDK 34 (Android 14/15).
2.  **Nerve**: WebSocket Client + Ed25519 Handshake.
3.  **Hand**: Accessibility Service basic wiring (log formatting).
4.  **Brain Stub**: `llama.cpp` placeholder integration.

## 6. GrapheneOS Tips
*   Enable "Exploit Protection Compatibility Mode" only if native libs crash (unlikely with modern llama.cpp).
*   Use "Storage Scopes" to limit file access to only the Syncthing folder.
