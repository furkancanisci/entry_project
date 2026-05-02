# 📱 Mobil Ekip - Firebase & API Setup

Mobil ekibin kullanması gereken tüm konfigürasyon, key'ler ve API detayları.

---

## 🔑 **1. Firebase Konfigürasyonu**

### Firebase Project Bilgileri
```
Project ID: saypex-ce566
Project Name: saypex
```

### Firebase Web Config (React/Web için)
```javascript
const firebaseConfig = {
  apiKey: "[Firebase Console → Project Settings → Web App → apiKey]",
  authDomain: "saypex-ce566.firebaseapp.com",
  projectId: "saypex-ce566",
  storageBucket: "saypex-ce566.appspot.com",
  messagingSenderId: "[Firebase Console → Project Settings → Cloud Messaging → Sender ID]",
  appId: "[Firebase Console → Project Settings → App ID]",
};
```

### Firebase Service Account (Backend yapılandırması - SADECE SERVER'DA)
```json
{
  "type": "service_account",
  "project_id": "saypex-ce566",
  "private_key_id": "3a4ca49d0702da3159b2de62cbf83c029bb866dd",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-fbsvc@saypex-ce566.iam.gserviceaccount.com",
  ...
}
```
⚠️ **Bu JSON'u mobil ekibe VERME!** Sadece backend (Render) kullanır.

---

## 📡 **2. Backend API Bilgileri**

### Base URL
```
Production: https://entry-project.onrender.com
Local Dev: http://localhost:8000
```

### Authentication
```
Method: JWT (JSON Web Token)
Header: Authorization: Bearer <JWT_TOKEN>
```

#### Login Endpoint
```
POST /api/token/
Content-Type: application/json

Request:
{
  "username": "user@example.com",
  "password": "password123"
}

Response:
{
  "access": "<JWT_TOKEN>",
  "refresh": "<REFRESH_TOKEN>"
}
```

#### Token Refresh
```
POST /api/token/refresh/
Content-Type: application/json

Request:
{
  "refresh": "<REFRESH_TOKEN>"
}

Response:
{
  "access": "<NEW_JWT_TOKEN>"
}
```

---

## 📱 **3. Device Registration**

### Register Device
```
POST /api/devices/
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

Request:
{
  "device_id": "unique-device-identifier",
  "shop_id": 2,
  "device_name": "iPhone 14 Pro",
  "push_token": "firebase-fcm-token-here",
  "os": "iOS"  // iOS, Android, Web
}

Response (201):
{
  "id": 1,
  "device_id": "unique-device-identifier",
  "shop_id": 2,
  "push_token": "firebase-fcm-token-here",
  "device_name": "iPhone 14 Pro",
  "created_at": "2026-05-02T12:00:00Z",
  "updated_at": "2026-05-02T12:00:00Z"
}
```

### Update Device Push Token
```
PUT /api/devices/<device_id>/
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

Request:
{
  "push_token": "new-firebase-fcm-token"
}

Response (200):
{
  "id": 1,
  "device_id": "unique-device-identifier",
  "push_token": "new-firebase-fcm-token",
  ...
}
```

### Get Device
```
GET /api/devices/<device_id>/
Authorization: Bearer <JWT_TOKEN>

Response (200):
{
  "id": 1,
  "device_id": "unique-device-identifier",
  "shop_id": 2,
  "push_token": "firebase-fcm-token-here",
  ...
}
```

---

## 📨 **4. Notification Settings**

### Set Notification Time Range & Token
```
POST /api/shops/<user_id>/notification-settings/
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

Request:
{
  "shop_id": 2,
  "notification_start_time": "09:00",  // HH:MM format (24-hour) - Bildirim başlangıç saati
  "notification_end_time": "18:00",    // HH:MM format (24-hour) - Bildirim bitiş saati
  "push_token": "firebase-fcm-token"   // Optional but recommended
}

Response (200):
{
  "message": "Bildirim saatleri kaydedildi.",
  "shop_id": 2,
  "shop_name": "Mağaza Adı",
  "notification_start_time": "09:00:00",
  "notification_end_time": "18:00:00",
  "notification_push_token_set": true
}
```

### Get Notification Settings
```
GET /api/shops/<user_id>/notification-settings/?shop_id=2
Authorization: Bearer <JWT_TOKEN>

Response (200):
{
  "shop_id": 2,
  "shop_name": "Mağaza Adı",
  "notification_start_time": "09:00:00",
  "notification_end_time": "18:00:00",
  "notification_push_token_set": true
}
```

**Important Notes:**
- `notification_start_time` and `notification_end_time` define the time window for notifications
- Notifications will **only** be sent if entry/exit records are created **between these times**
- Both fields are required
- `notification_start_time` must be before `notification_end_time`
- Format: `HH:MM` or `HH:MM:SS` (24-hour format)
- Example: Start at 09:00 (9 AM), end at 18:00 (6 PM) → Notifications only during business hours

---

## 📍 **5. Entry/Exit Records**

### Submit Entry/Exit Record
```
POST /api/entry-exit-record/
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

Request:
{
  "shop_id": 2,
  "device_id": "device-123",
  "is_entry": true,
  "is_exit": false,
  "rssi": -55,
  "created_at": "2026-05-02 15:30:00"  // Server saat dilimi
}

Response (201):
{
  "id": 1681,
  "shop_id": 2,
  "device_id": "device-123",
  "is_entry": true,
  "is_exit": false,
  "rssi": -55,
  "created_at": "2026-05-02T15:30:00Z",
  "notification_sent": true
}
```

---

## 🔔 **6. Firebase Push Token Alma**

### JavaScript/Web
```javascript
import { getMessaging, getToken } from "firebase/messaging";

const messaging = getMessaging();

// Request notification permission
Notification.requestPermission().then((permission) => {
  if (permission === "granted") {
    // Get token
    getToken(messaging, {
      vapidKey: "YOUR_VAPID_KEY"  // See below
    }).then((token) => {
      console.log("FCM Token:", token);
      // Send to backend via /api/devices/ or update endpoint
    });
  }
});
```

### React Native (react-native-firebase)
```javascript
import messaging from '@react-native-firebase/messaging';

// Request permission
await messaging.requestPermission();

// Get token
const token = await messaging.getToken();
console.log("FCM Token:", token);
```

### Flutter (firebase_messaging)
```dart
import 'package:firebase_messaging/firebase_messaging.dart';

final token = await FirebaseMessaging.instance.getToken();
print('FCM Token: $token');
```

---

## 📢 **7. Firebase Topic Subscription**

### Topic Format
```
shop_<shop_id>

Examples:
- shop_1
- shop_2
- shop_5
```

### Subscribe to Topic (JavaScript)
```javascript
import { getMessaging } from "firebase/messaging";

// Note: Topic subscription is server-side or handled by FCM SDK
// Mobile app should listen on this topic via Firebase service worker

// In service-worker.js:
importScripts("https://www.gstatic.com/firebasejs/9.0.0/firebase-app.js");
importScripts("https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging.js");

firebase.initializeApp({
  // Firebase config here
});

const messaging = firebase.messaging();

// Handle foreground messages
messaging.onMessage((payload) => {
  console.log("Message received:", payload);
  // Display notification to user
});

// Handle background messages (automatic)
```

### Subscribe to Topic (React Native)
```javascript
import messaging from '@react-native-firebase/messaging';

messaging()
  .subscribeToTopic('shop_2')
  .then(() => console.log('Subscribed to shop_2'));

// Listen to messages
messaging().onMessage(async (remoteMessage) => {
  console.log('Notification:', remoteMessage.notification);
  // Handle notification
});
```

### Subscribe to Topic (Flutter)
```dart
import 'package:firebase_messaging/firebase_messaging.dart';

FirebaseMessaging.instance.subscribeToTopic('shop_2');

// Listen to messages
FirebaseMessaging.onMessage.listen((RemoteMessage message) {
  print('Notification: ${message.notification?.title}');
});
```

---

## 📊 **8. Sample API Flow**

### Complete User Journey
```
1. User Login
   POST /api/token/ → Get JWT

2. Register Device
   POST /api/devices/
   Body: { device_id, shop_id, push_token }

3. Get Push Token
   Use Firebase SDK to get FCM token

4. Set Notification Time Range
   POST /api/shops/<user_id>/notification-settings/
   Body: { shop_id, notification_start_time, notification_end_time }

5. Subscribe to Topic
   messaging().subscribeToTopic('shop_2')

6. Listen for Messages
   messaging().onMessage((payload) => {...})

7. Submit Entry/Exit Record
   POST /api/entry-exit-record/
   → Backend auto-sends notification to shop_2 topic
   → Mobile receives notification
```

---

## 🔐 **9. VAPID Key (Web Push)**

### Generate VAPID Key (Firebase Console)
```
1. Go to Firebase Console
2. Project Settings → Cloud Messaging
3. Web Configuration → Generate Key Pair
4. Copy Public Key
```

### Example VAPID Key
```
BEqwDW7pBxLGwfgKqFc8d8hG7wX4YkZqPwXx...
```

Use in web app:
```javascript
getToken(messaging, {
  vapidKey: "BEqwDW7pBxLGwfgKqFc8d8hG7wX4YkZqPwXx..."
})
```

---

## ✅ **10. Checklist for Mobile Team**

- [ ] Firebase Project ID: `saypex-ce566`
- [ ] Firebase Web Config obtained from Firebase Console
- [ ] Push notification permission requested and granted
- [ ] Firebase SDK initialized in app
- [ ] JWT login endpoint working
- [ ] Device registration working via `/api/devices/`
- [ ] Push token obtained and stored
- [ ] Notification start/end times saved via `/api/shops/<user_id>/notification-settings/`
   - Example: 09:00 - 18:00 (business hours)
- [ ] Subscribed to `shop_<shop_id>` topic
- [ ] `onMessage` listener implemented
- [ ] Service worker configured (web only)
- [ ] Entry/exit record submission working
- [ ] Notifications received when records submitted

---

## 🚀 **11. Testing Notifications**

### Manual Test via API
```bash
# 1. Get JWT Token
curl -X POST "https://entry-project.onrender.com/api/token/" \
  -H "Content-Type: application/json" \
  -d '{"username":"user@example.com", "password":"pass"}'

# 2. Register Device
curl -X POST "https://entry-project.onrender.com/api/devices/" \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"device_id":"test-device","shop_id":2,"push_token":"firebase-token","device_name":"Test"}'

# 3. Set Notification Time Range (09:00 - 18:00)
curl -X POST "https://entry-project.onrender.com/api/shops/1/notification-settings/" \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"shop_id":2,"notification_start_time":"09:00","notification_end_time":"18:00"}'

# 4. Submit Entry Record at 15:30 (within time range - will trigger notification)
curl -X POST "https://entry-project.onrender.com/api/entry-exit-record/" \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"shop_id":2,"device_id":"test-device","is_entry":true,"is_exit":false,"rssi":-55,"created_at":"2026-05-02 15:30:00"}'

# 5. Submit Entry Record at 23:00 (outside time range - will NOT trigger notification)
curl -X POST "https://entry-project.onrender.com/api/entry-exit-record/" \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"shop_id":2,"device_id":"test-device","is_entry":true,"is_exit":false,"rssi":-55,"created_at":"2026-05-02 23:00:00"}'

# Check if notification was sent
# → Only request #4 should trigger notification (15:30 is between 09:00-18:00)
# → Request #5 will NOT send notification (23:00 is outside 09:00-18:00)
```

---

## 📧 **Support**

For issues or questions:
- Backend logs: Check Render dashboard
- Firebase Console: For project settings & debugging
- Mobile SDK docs:
  - Web: https://firebase.google.com/docs/cloud-messaging/js/client
  - React Native: https://rnfirebase.io/messaging/usage
  - Flutter: https://firebase.flutter.dev/docs/messaging/overview/
