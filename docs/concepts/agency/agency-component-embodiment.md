---
title: Agency Component – Embodiment & Spatial State
---

# Embodiment & Spatial State

## Embodiment Types

Embodiment is a core element of AICO. It is used to represent AICO in the user's environment and to provide a visual interface to the user. This can have multiple embodiments, e.g. a 3D avatar, a 2D image, or a text description, or a holographic representation OR aico can be embodies in a robot or other device.

### 3D Living Space

The Embodiment & Spatial State component connects agency to AICO’s **3D avatar and living‑space**:

- Represents AICO in a flat with multiple rooms (desk/office, couch/living room, bedroom, kitchen, bathroom, etc.).  
- Maps internal lifecycle and activity state (working, reading, sleeping, idle, self‑care) to room and posture.  
- Provides a continuous, spatial visualization of what AICO is "doing" even when no chat is active.

It acts as the primary **visual interface** to agency, complementing text conversation by showing:

- Current focus and activity.  
- Transitions between modes (moving rooms as goals change).  
- Sleep and wake cycles.

Future work will specify the avatar control protocol, room state machine, and UX patterns.
