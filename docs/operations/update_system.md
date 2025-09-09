---
title: Update System
---

# Update System

## Overview

The AICO Update System is a critical infrastructure component that enables secure, reliable, and user-friendly updates for both the frontend (Flutter) and backend (Python) components. It supports configurations where frontend and backend may be on the same device or separated, while ensuring minimal disruption to the user experience.

The Update System is designed with the following core principles:

- **Security**: All updates are cryptographically verified to ensure authenticity and integrity
- **Reliability**: Updates are atomic with rollback capabilities to prevent system corruption
- **User Control**: Users can define update schedules while critical security updates can be prioritized
- **Minimal Disruption**: Updates occur with minimal interruption to the user experience
- **Flexibility**: Supports various deployment scenarios including separated frontend/backend

## Architecture

The Update System is implemented as a dedicated module within AICO's Infrastructure Module:

```
Infrastructure Module
└── Update System
    ├── Component: Version Management
    └── Component: Atomic Updates
```

### Version Management Component

The Version Management component is responsible for:

- Tracking current versions of all system components
- Checking for updates on a user-defined schedule
- Managing update policies (auto vs. manual, critical vs. optional)
- Handling update notifications to users
- Enforcing security policies for updates

### Atomic Updates Component

The Atomic Updates component is responsible for:

- Executing the actual update process
- Ensuring data integrity during updates
- Managing graceful restarts of components
- Implementing rollback capabilities if updates fail
- Coordinating updates between frontend and backend

## Communication Protocol

The Update System communicates via the ZeroMQ message bus using the following topics:

| Topic | Description |
|-------|-------------|
| `update.check.request` | Request to check for available updates |
| `update.check.response` | Response containing update availability information |
| `update.available` | Notification that updates are available |
| `update.download.progress` | Progress updates during download |
| `update.download.complete` | Notification that download is complete |
| `update.install.request` | Request to install downloaded updates |
| `update.install.progress` | Progress updates during installation |
| `update.install.complete` | Notification that installation is complete |
| `update.restart.required` | Notification that restart is required |
| `update.restart.scheduled` | Information about scheduled restart |

## Update Process Flow

### Update Check Process

1. The Update System checks for updates on a user-defined schedule
2. For critical security updates, the system can force an update check regardless of schedule
3. The system contacts the update server using secure HTTPS connections
4. The server responds with available updates and their metadata (version, size, criticality)
5. Updates are verified using TUF's security mechanisms

### Update Installation Process

#### Preparation Phase
- Download updates in the background with progress reporting
- Verify cryptographic signatures of downloaded packages
- Prepare update packages for installation

#### Coordination Phase
- Notify user about pending updates (UI notification)
- For non-critical updates: Allow user to schedule the update
- For critical updates: Notify that update will be applied at next opportunity

#### Installation Phase
- Backend creates a backup of critical data
- Signal all components to prepare for update
- Apply updates to inactive components first
- Use atomic file operations to ensure consistency

#### Restart Phase
- Graceful shutdown of components
- Start updated components
- Verify successful update
- If update fails, roll back to previous version

## Handling Separated Frontend/Backend

The Update System supports configurations where frontend and backend may be on different devices:

### Backend-only Updates
- Backend updates itself independently
- Notifies connected frontends about the update
- Coordinates graceful disconnection and reconnection

### Frontend-only Updates
- Frontend updates itself independently
- Maintains compatibility with backend API versions

### Coordinated Updates
- When both need updating, backend updates first
- Frontend updates only after backend update is confirmed successful

## User Experience Considerations

To minimize user disruption, the Update System implements:

- **Background downloads**: Updates download in the background without affecting performance
- **Scheduled updates**: Users can schedule updates for convenient times
- **Seamless restarts**: State preservation so conversations can continue after updates
- **Clear notifications**: Non-intrusive update notifications
- **Progress indicators**: Update progress visibility when updates are being applied

## Security Considerations

The Update System implements robust security measures:

- **Cryptographic verification**: All updates are signed and verified using TUF security mechanisms
- **Secure transport**: Updates are downloaded over HTTPS
- **Integrity checking**: Package integrity is verified before and after installation
- **Rollback capability**: System can revert to previous version if update fails
- **Privilege separation**: Update installation uses minimal required privileges

## Technical Implementation

### Backend (Python) Update System

The backend update system uses **TUFup** as the core update framework, which provides:

- Strong security through The Update Framework (TUF)
- Support for delta updates to minimize bandwidth usage
- Cryptographic verification of updates
- Compatibility with any type of application bundle
- Support for different release channels (stable, beta, etc.)

### Frontend (Flutter) Update System

The frontend update system uses a hybrid approach:

- For mobile platforms:
  - `upgrader` package for iOS and Android app store updates
  - Custom update logic for sideloaded apps

- For desktop platforms:
  - Custom update mechanism using the backend update service
  - Platform-specific packaging (MSIX for Windows, DMG for macOS)

## Configuration Options

The Update System provides the following configuration options:

| Option | Description | Default |
|--------|-------------|---------|
| `update.check_interval` | Interval between update checks (hours) | 24 |
| `update.auto_download` | Automatically download updates | true |
| `update.auto_install` | Automatically install non-critical updates | false |
| `update.critical_install` | Automatically install critical updates | true |
| `update.notify_available` | Notify when updates are available | true |
| `update.preferred_time` | Preferred time for updates (HH:MM) | 03:00 |
| `update.channel` | Update channel (stable, beta, dev) | stable |
