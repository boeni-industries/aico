# Studio AI - Bulk User Deletion Guide

## Endpoint

**Bulk Delete Users**

```
POST /api/v1/admin/users/bulk-delete
Authorization: Bearer {admin_jwt_token}
Content-Type: application/json

{
  "user_uuids": ["uuid1", "uuid2", "uuid3"],
  "hard_delete": false,
  "confirm": true,
  "reason": "Optional reason"
}
```

## Parameters

- **user_uuids** (required): Array of user UUIDs to delete (1-100 users)
- **hard_delete** (optional, default: false):
  - `false` = Soft delete (deactivate users, set `is_active=false`)
  - `true` = Hard delete (permanently remove from database)
- **confirm** (required): Must be `true` to proceed
- **reason** (optional): Reason for deletion (logged in audit trail)

## Response

```json
{
  "success": true,
  "total_requested": 3,
  "successful": 3,
  "failed": 0,
  "results": [
    {
      "user_uuid": "uuid1",
      "success": true,
      "error": null
    },
    {
      "user_uuid": "uuid2",
      "success": true,
      "error": null
    },
    {
      "user_uuid": "uuid3",
      "success": false,
      "error": "User not found"
    }
  ]
}
```

## Usage Example

**User Request:** "Delete users Alice, Bob, and Charlie"

**AI Response:** "I'll delete those 3 users. This will deactivate their accounts (soft delete)."

**API Call:**
```json
POST /api/v1/admin/users/bulk-delete
{
  "user_uuids": ["alice-uuid", "bob-uuid", "charlie-uuid"],
  "hard_delete": false,
  "confirm": true,
  "reason": "User requested bulk deletion"
}
```

## Important Notes

- Maximum 100 users per request
- Operation continues even if individual deletions fail
- All successful deletions are committed together
- Each deletion is logged in audit trail
- Soft delete is recommended (allows recovery)
