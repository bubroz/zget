# Increase Logo Size & Visibility

The user reports that the "zget" logo is too small, especially on mobile devices. We will increase the logo dimensions in the header to ensure it's legible and has a premium presence.

## Proposed Changes

### [Component] UI Header Logo

#### [MODIFY] [app.js](file:///Users/base/Projects/zget/src/zget/server/static/components/app.js)

- Increase desktop logo size from `32px` to `48px`.
- Increase mobile logo size from `18px` to `36px`.
- Ensure aspect ratio is maintained.
- Adjust header height if necessary to accommodate the larger logo.

## Verification Plan

### Automated Tests

- None applicable for this visual change.

### Manual Verification

- View the application on desktop and mobile (using the phone or DevTools responsive mode).
- Take a screenshot of the new logo size on mobile and share it with the user for approval.
