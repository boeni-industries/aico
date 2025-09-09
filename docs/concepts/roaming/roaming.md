---
title: Device Roaming Architecture
---

# Device Roaming

## Definition

**Roaming** is AICO's ability to seamlessly transition between devices while maintaining continuity of state, context, and capabilities, enabling a consistent user experience across the device ecosystem.

## Overview

AICO supports **device roaming** where the frontend and backend can operate independently across different devices and platforms. This enables flexible deployment patterns based on device capabilities and user needs.

## Core Concepts

### Frontend-Backend Separation
- **Frontend**: Flutter UI that handles user interaction and presentation
- **Backend**: Python service that handles AI processing, data storage, and autonomous agency
- **Detachable**: Frontend and backend can run on different devices when needed

### Roaming Patterns

#### **Coupled Roaming**
Frontend and backend roam together to the same device:
- Desktop → Desktop
- Mobile → Mobile (when backend is supported)

#### **Detached Roaming** 
Frontend roams to a device without backend capability:
- Frontend: Lightweight device (tablet, phone, smart display)
- Backend: Remains on powerful device (desktop, server)
- Connection: Network communication between frontend and backend

## Use Cases

### Coupled Scenarios
- **Home Office**: Desktop with full AICO stack
- **Mobile Work**: Laptop with complete AICO installation
- **Powerful Tablet**: iPad Pro/Surface Pro with backend capability

### Detached Scenarios
- **Smart Display**: Kitchen display shows AICO UI, backend runs on home server
- **Phone Interface**: Mobile frontend connects to desktop backend
- **AR Glasses**: Lightweight frontend, backend on paired device
- **Car Integration**: Dashboard frontend, backend on phone/cloud

## Technical Architecture

### Communication Modes
- **Local**: Frontend and backend on same device (IPC/local sockets)
- **Network**: Frontend and backend on different devices (REST/WebSocket/gRPC)
- **Hybrid**: Multiple frontends connecting to single backend

### State Synchronization
- **Frontend State**: UI state, user preferences, temporary display data
- **Backend State**: AI models, conversation history, memory, autonomous goals
- **Sync Protocol**: Real-time state synchronization between detached components

## Security Implications

### Coupled Deployment
- Single device security boundary
- Local encryption at rest
- No network exposure required

### Detached Deployment  
- Network communication security (TLS/encryption)
- Authentication between frontend and backend
- Distributed trust model
- Network-based attack surface

## Platform Capabilities

### Frontend Platforms

| Platform | Form Factor | Roaming Support | Capabilities | Limitations |
|----------|------------|-----------------|--------------|-------------|
| **Desktop** | Windows/macOS/Linux | Full (Coupled/Detached) | Complete UI, avatar rendering, all input modes | None |
| **Mobile** | iOS/Android | Full (Coupled/Detached) | Complete UI, optimized avatar, touch/voice | Resource constraints |
| **Tablet** | iPadOS/Android | Full (Coupled/Detached) | Complete UI, touch-optimized, stylus support | Resource constraints |
| **Smart Display** | Various | Frontend-only | Voice-first UI, simplified avatar | Requires backend connection |
| **AR Glasses** | Various | Frontend-only | Minimal UI, spatial overlay | Requires backend connection |
| **Car Systems** | Various | Frontend-only | Voice-first, simplified UI | Requires backend connection |
| **Wearables** | WearOS/WatchOS | Frontend-only | Minimal UI, notifications | Requires backend connection |
| **Web Browser** | Any | Frontend-only | Standard UI in browser | Requires backend connection |

### Backend Platforms

| Platform | Form Factor | Roaming Support | Capabilities | Limitations |
|----------|------------|-----------------|--------------|-------------|
| **Desktop** | Windows/macOS/Linux | Full | Complete AI stack, all databases | None |
| **Server** | Linux | Full | Complete AI stack, optimized performance | Fixed location |
| **High-end Mobile** | iOS/Android | Limited | Basic AI processing, simplified storage | Resource constraints |
| **NAS/Home Server** | Various | Full | Complete AI stack, optimized storage | Fixed location |
| **Single-board Computer** | RPi/Jetson | Limited | Basic AI processing, optimized storage | Performance constraints |

!!! info Current restrictions
    Currently, only platforms that offer **Full** backend support are considered for backend roaming. Platforms with **Limited** backend support are not yet supported.

### Roaming Compatibility Matrix

| Frontend → Backend | Desktop | Server | High-end Mobile | NAS/Home Server | Single-board Computer |
|-------------------|---------|--------|-----------------|-----------------|------------------------|
| **Desktop** | Coupled/Detached | Detached | Detached | Detached | Detached |
| **Mobile** | Detached | Detached | Coupled/Detached | Detached | Detached |
| **Tablet** | Detached | Detached | Detached | Detached | Detached |
| **Smart Display** | Detached | Detached | Detached | Detached | Detached |
| **AR Glasses** | Detached | Detached | Detached | Detached | Detached |
| **Car Systems** | Detached | Detached | Detached | Detached | Detached |
| **Wearables** | Detached | Detached | Detached | Detached | Detached |
| **Web Browser** | Detached | Detached | Detached | Detached | Detached |

