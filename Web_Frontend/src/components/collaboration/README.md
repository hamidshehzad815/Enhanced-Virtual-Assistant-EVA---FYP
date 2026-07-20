# AI Chat Collaboration - Frontend Implementation

## Overview
This implementation adds comprehensive frontend support for AI Chat Collaboration features. The implementation consists of React components that display collaboration-related responses from the backend AI server within the existing chat interface.

## Key Principles
- **No backend modifications** - Only frontend rendering of existing backend responses
- **Seamless integration** - Collaboration messages appear naturally within chat flow
- **Responsive design** - Works on desktop, tablet, and mobile devices
- **Error handling** - Backend errors displayed clearly and exactly as received
- **No custom state management** - All collaboration state comes from backend responses

## Component Architecture

### Core Components

#### 1. CollaborationMessage
**File:** `src/components/collaboration/CollaborationMessage.jsx`

The main wrapper component that detects collaboration data type and renders appropriate sub-components.

**Props:**
- `data` (object) - Collaboration data from AI response
- `onSelectTimeSlot` (function) - Callback when user selects a suggested time
- `messageType` (string) - Optional message type hint

**Supported Data Types:**
- `task_created` - Displays newly created task with collaborators
- `invite_sent` - Shows collaboration invitations sent
- `conflict` - Displays scheduling conflict with suggested times
- `status_update` - Shows collaboration status changes
- `collaborators_list` - Lists collaborators
- `error` - Displays error messages

#### 2. CollaborationSummaryCard
**File:** `src/components/collaboration/CollaborationSummaryCard.jsx`

Displays task details with collaboration context (title, date, time, owner, collaborators).

**Props:**
- `task` (object) - Task data {title, due_date, duration, owner}
- `collaborationStatus` (string) - Current collaboration status
- `collaborators` (array) - List of collaborators
- `expandable` (boolean) - Allow expand/collapse of collaborator list
- `defaultExpanded` (boolean) - Initial expand state
- `showOwner` (boolean) - Display task owner
- `maxDisplayCollaborators` (number) - Max to show before "more" indicator

#### 3. StatusIndicator
**File:** `src/components/collaboration/StatusIndicator.jsx`

Visual badge showing collaborator or invitation status.

**Props:**
- `status` (string) - Status value: pending, accepted, rejected, removed, expired, cancelled
- `size` (string) - Badge size: sm, md, lg
- `showLabel` (boolean) - Show text label
- `label` (string) - Custom label text

**Status Types:**
- **Pending** (yellow) - Awaiting response
- **Accepted** (green) - Collaborator accepted
- **Rejected** (red) - Collaborator rejected
- **Removed** (gray) - Removed from collaboration
- **Expired** (red) - Invitation expired
- **Cancelled** (gray) - Invitation cancelled

#### 4. CollaboratorsList
**File:** `src/components/collaboration/CollaboratorsList.jsx`

Displays list of collaborators with individual status and optional actions.

**Props:**
- `collaborators` (array) - Collaborator list [{_id, name, email, status}]
- `onRemove` (function) - Callback for remove action
- `onResend` (function) - Callback for resend action
- `maxDisplay` (number) - Limit display with "+N more" indicator
- `compact` (boolean) - Use compact layout

#### 5. SuggestedTimeSlots
**File:** `src/components/collaboration/SuggestedTimeSlots.jsx`

Displays suggested alternative time slots for scheduling conflicts with selection flow.

**Props:**
- `slots` (array) - Available time slots [{start_time, end_time, label, reason}]
- `onSelectSlot` (function) - Callback when user selects a slot
- `taskTitle` (string) - Task name for confirmation message
- `isLoading` (boolean) - Show loading state during submission

**Flow:**
1. User clicks a suggested time
2. Confirmation panel appears
3. User confirms or cancels
4. Selection sent back to AI as new message

#### 6. LoadingState
**File:** `src/components/collaboration/LoadingState.jsx`

Displays loading indicators during collaboration operations.

**Props:**
- `type` (string) - Operation type: creating, sending, checking, scheduling, updating, general
- `message` (string) - Custom message
- `size` (string) - Badge size: sm, md, lg

#### 7. ErrorMessage
**File:** `src/components/collaboration/ErrorMessage.jsx`

Displays backend error messages with appropriate styling.

**Props:**
- `message` (string) - Error message from backend (displayed exactly as received)
- `title` (string) - Error title
- `type` (string) - Message type: error, warning, conflict, info
- `onDismiss` (function) - Callback for dismiss
- `dismissible` (boolean) - Show dismiss button
- `details` (object/string) - Additional error details

## Data Flow

### From Backend to Frontend

```
Backend AI Response
    ↓
Chat API (/api/chat/process)
    ↓
ChatContext.sendMessage()
    ↓
Response.data → stored as collaborationData
    ↓
Message object {
    text,
    collaborationData,
    isEva,
    timestamp,
    ...
}
    ↓
Saved to localStorage & state
    ↓
Chat.jsx renders messages
    ↓
DemoChatBubble receives collaborationData
    ↓
CollaborationMessage detects type
    ↓
Renders appropriate sub-component
```

### Time Slot Selection Flow

```
User clicks suggested time
    ↓
SuggestedTimeSlots confirmation panel
    ↓
User confirms selection
    ↓
onSelectTimeSlot(slot) callback
    ↓
Chat.jsx → handleSelectTimeSlot()
    ↓
Sends formatted message to AI
    ↓
Backend processes and responds
    ↓
New message with updated collaboration data
```

## Integration Points

### ChatContext Enhancement
**File:** `src/contexts/ChatContext.jsx`

Changes made:
1. `mapBackendMessages()` - Extracts `collaboration_data` from AI response
2. `sendMessage()` - Includes `response?.data` as `collaborationData` in reply message

### DemoChatBubble Enhancement
**File:** `src/components/DemoChatBubble.jsx`

Changes made:
1. Accepts `collaborationData` prop
2. Accepts `onSelectTimeSlot` callback
3. Renders CollaborationMessage component when collaboration data present
4. Maintains backward compatibility with text-only messages

### Chat Component Enhancement
**File:** `src/pages/Chat.jsx`

Changes made:
1. Added `handleSelectTimeSlot()` function
2. Passes `collaborationData` to DemoChatBubble
3. Passes `onSelectTimeSlot` handler to DemoChatBubble

## Styling & Responsiveness

All components include:
- **Light/Dark mode support** - Uses CSS variables
- **Mobile-first approach** - Base styles for mobile, enhanced for larger screens
- **Responsive breakpoints:**
  - `(max-width: 480px)` - Mobile devices
  - `(max-width: 768px)` - Tablets
  - Desktop - Full design

**CSS Features:**
- Flexbox layouts for responsive behavior
- Touch-friendly button sizes (min 44x44px for touch targets)
- Readable font sizes on all devices
- Proper spacing and overflow handling
- Smooth transitions and animations

## Error Handling

### Backend Error Response
```json
{
  "status": "fail",
  "message": "Collaborator busy on Friday 3pm",
  "data": {
    "conflict": true,
    "collaborator": "John Doe",
    "time_range": "2:00 PM - 4:00 PM"
  }
}
```

### Frontend Rendering
1. ChatContext extracts `response?.data` as collaboration data
2. CollaborationMessage detects `error` type
3. ErrorMessage component displays message exactly as received
4. Optional error details shown if provided

### No Custom Error Logic
- Backend errors displayed verbatim
- No custom error messages generated on frontend
- Error context preserved for debugging

## Usage Examples

### 1. Render collaboration message in chat
```jsx
<DemoChatBubble
  text={msg.text}
  isEva={msg.isEva}
  collaborationData={msg.collaborationData}
  onSelectTimeSlot={handleSelectTimeSlot}
/>
```

### 2. Access specific collaboration data in backend response
```javascript
// Backend returns:
{
  response_text: "I've created your study session and invited...",
  data: {
    task_created: { _id, title, due_date, collaborators: [...] },
    invites_sent: [ { name, email, status: "pending" } ]
  }
}

// Frontend extracts and renders automatically
// CollaborationMessage detects task_created type
// Displays CollaborationSummaryCard + CollaboratorsList
```

### 3. Handle scheduling conflict
```javascript
// Backend returns:
{
  response_text: "John is busy at that time. Here are alternatives:",
  data: {
    conflict_message: "John Doe is unavailable 3pm-5pm Friday",
    suggested_times: [
      { start_time: "...", end_time: "...", label: "Friday 5pm" },
      { start_time: "...", end_time: "...", label: "Saturday 10am" }
    ]
  }
}

// Frontend:
// 1. CollaborationMessage detects conflict type
// 2. Displays conflict message
// 3. Shows SuggestedTimeSlots component
// 4. User selects one → handleSelectTimeSlot sends new message
```

## Testing Checklist

- [ ] Task created message displays correctly
- [ ] Multiple collaborators show with individual status
- [ ] Suggested time slots appear and can be selected
- [ ] Selected time slot sends as new message
- [ ] Status indicators show correct colors/states
- [ ] Error messages display backend text exactly
- [ ] Components responsive on mobile (< 480px)
- [ ] Components responsive on tablet (< 768px)
- [ ] Expandable collaborator lists work
- [ ] Loading states appear during operations
- [ ] Collaboration data persists through page reload
- [ ] Existing chat functionality not broken

## Files & Locations

```
src/components/
├── collaboration/
│   ├── StatusIndicator.jsx
│   ├── StatusIndicator.css
│   ├── CollaboratorsList.jsx
│   ├── CollaboratorsList.css
│   ├── CollaborationSummaryCard.jsx
│   ├── CollaborationSummaryCard.css
│   ├── SuggestedTimeSlots.jsx
│   ├── SuggestedTimeSlots.css
│   ├── CollaborationMessage.jsx
│   ├── CollaborationMessage.css
│   ├── LoadingState.jsx
│   ├── LoadingState.css
│   ├── ErrorMessage.jsx
│   ├── ErrorMessage.css
│   └── index.js
├── DemoChatBubble.jsx (ENHANCED)
├── DemoChatBubble.css (ENHANCED)

src/contexts/
├── ChatContext.jsx (ENHANCED)

src/pages/
├── Chat.jsx (ENHANCED)
```

## No Breaking Changes

All existing functionality preserved:
- ✓ Chat history loading
- ✓ Message sending
- ✓ Voice input
- ✓ Conversation management
- ✓ Calendar sync
- ✓ Settings
- ✓ Authentication
- ✓ All other features

New functionality is purely additive - collaboration components only render when collaboration data present in AI response.

## Maintenance Notes

- **Adding new collaboration message types:** Update `getMessageType()` in CollaborationMessage.jsx
- **Modifying error display:** Update ErrorMessage.jsx and error detection in CollaborationMessage.jsx
- **Changing collaboration UI:** Edit respective component files - all styles modular and independent
- **Adding new status types:** Update StatusIndicator.jsx with new status case
- **Responsive adjustments:** Modify media queries in respective component CSS files

## Performance Considerations

- Components are lightweight and render only when needed
- Collaboration data doesn't duplicate message data (stored once)
- No polling or subscriptions - only backend-driven updates
- LocalStorage used for persistence (existing chat pattern)
- No external dependencies added

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Requires ES6+ support
- Responsive design tested on:
  - iOS Safari
  - Android Chrome
  - Chrome Desktop
  - Firefox Desktop
  - Safari Desktop
