# Mobil API Guide

Bu doküman mobil ekip için mevcut backend akışını, gerekli payload'ları ve mağaza bazlı güvenlik bildirimi özelliğini açıklar.

## 1. Genel Mimari

Mobil uygulama iki temel işi yapar:

1. Kullanıcının bağlı olduğu mağazayı ya da mağazaları getirir.
2. Cihazdan gelen giriş/çıkış ölçümlerini sunucuya gönderir.

Yeni eklenen güvenlik özelliği ile mağaza sahibi, belirli bir saat seçebilir. Bu saatten sonra oluşan giriş/çıkış kayıtları için sunucu push bildirim göndermeyi dener.

## 2. Temel Kurallar

- Tüm zaman alanları sunucu tarafında `HH:MM` veya `HH:MM:SS` formatında kabul edilir.
- Bildirim saati, mağaza bazında tutulur.
- Bildirimlerin gerçekten gönderilebilmesi için mağazaya ait push token kaydedilmiş olmalıdır.
- Sunucuda `FCM_SERVER_KEY` tanımlı değilse push denemesi yapılmaz.
- Kayıt endpoint'i `EntryExitRecord` oluşturur, saat kontrolü yapar ve uygunsa bildirim göndermeye çalışır.

## 3. Kimlik Doğrulama

Mobil giriş için mevcut JWT tabanlı oturum kullanılabilir.

### Login

`POST /api/login/`

#### Request

```json
{
  "username": "demo",
  "password": "secret123"
}
```

#### Response

```json
{
  "access": "jwt_access_token",
  "refresh": "jwt_refresh_token",
  "user_id": 12,
  "username": "demo",
  "email": "demo@example.com",
  "joined_date": "2026-05-01",
  "shop_name": "Merkez Mağaza",
  "is_superuser": false,
  "is_staff": false
}
```

Mobil uygulama sonraki yetkili isteklerde `Authorization: Bearer <access>` başlığı kullanmalıdır.

## 4. Mağaza Bildirim Saatini Kaydetme

Bu endpoint, mağaza sahibi veya yetkili kullanıcı tarafından seçilen saati kaydeder. Aynı istekte push token da gönderilebilir.

### Endpoint

`POST /api/shops/{user_id}/notification-settings/`

### Purpose

- Seçilen mağaza için bildirim saatini kaydeder.
- İstenirse mağazaya ait push token'ı da saklar.

### Request Body

```json
{
  "shop_id": 3,
  "notification_time": "01:00",
  "push_token": "fcm_device_token_optional"
}
```

### Accepted Aliases

- `notification_time`
- `hour`
- `time`

### Notes

- `shop_id` zorunludur.
- `notification_time` zorunludur.
- `push_token` isteğe bağlıdır ama gerçek push gönderimi için gereklidir.
- Zaman alanı `01:00`, `01:00:00` gibi formatlarda gönderilebilir.

### Response

```json
{
  "message": "Bildirim saati kaydedildi.",
  "shop_id": 3,
  "shop_name": "Merkez Mağaza",
  "notification_time": "01:00:00",
  "notification_push_token_set": true
}
```

### Validation Errors

```json
{
  "error": "shop_id gereklidir."
}
```

```json
{
  "error": "Geçersiz saat formatı. HH:MM veya HH:MM:SS kullanın."
}
```

## 5. Kayıt Gönderme API'si

Mobil taraf cihaz ölçüm verisini bu endpoint'e gönderir. Sunucu kaydı oluşturur ve mağazanın bildirim saati geçilmişse push gönderimini dener.

### Endpoint

Tercih edilen yol:

`POST /api/entry-exit-record/`

Alternatif yol:

`POST /api/records/add/`

### Request Format

Bu endpoint bir liste bekler.

```json
[
  {
    "shopid": 3,
    "deviceid": 9,
    "isentry": true,
    "isexit": false,
    "rssi": -61,
    "created_at": "2026-05-01 01:05:00"
  }
]
```

### Alanlar

- `shopid`: Mağaza ID'si.
- `deviceid`: Cihaz ID'si.
- `isentry`: Giriş kaydı mı?
- `isexit`: Çıkış kaydı mı?
- `rssi`: Ölçüm sinyal gücü.
- `created_at`: Kayıt zamanı, `YYYY-MM-DD HH:MM:SS` formatında.

### Response

```json
{
  "message": "1 records successfully added.",
  "records": [
    {
      "id": 145,
      "shop": 3,
      "device": 9,
      "shop_name": 3,
      "device_name": 9,
      "is_entry": true,
      "created_at": "2026-05-01T01:05:00"
    }
  ]
}
```

### Error Examples

```json
{
  "error": "Data must be a list of records"
}
```

```json
{
  "error": "Missing required fields. Required: ['shopid', 'deviceid', 'isentry', 'isexit', 'rssi', 'created_at']"
}
```

```json
{
  "error": "Invalid datetime format for created_at. Use YYYY-MM-DD HH:MM:SS"
}
```

## 6. Bildirim Mantığı

Sunucu şu koşullarda bildirim göndermeyi dener:

1. Mağazada `notification_time` tanımlıysa.
2. Gelen kaydın `created_at` saati bu saatten büyük veya eşitse.
3. Kayıt giriş ya da çıkış olarak işaretlenmişse.
4. Mağaza için push token saklanmışsa.
5. Sunucuda `FCM_SERVER_KEY` tanımlıysa.

Bildirim içeriği örnek olarak şöyle oluşturulur:

- Başlık: `Merkez Mağaza için güvenlik bildirimi`
- Mesaj: `Merkez Mağaza mağazasında 01:05 saatinden sonra giriş kaydı oluştu.`

## 7. Push Token Gereksinimi

Gerçek push bildirimi için mobil uygulama cihazdan bir push token alıp backend'e göndermelidir.

Beklenen token kaynakları:

- Firebase Cloud Messaging
- Expo push token
- APNs tabanlı kendi push çözümünüz

Mevcut backend tarafı FCM HTTP API üzerinden gönderim yapacak şekilde hazırlanmıştır. Eğer farklı bir push altyapısı kullanılacaksa backend tarafında gönderim adaptasyonu gerekir.

## 8. Mağaza Verisini Okuma

Mağaza listesini mevcut kullanıcıya göre almak için kullanıcıya bağlı mağaza endpoint'leri kullanılabilir.

### Endpoint

`GET /api/users/{user_id}/shops/`

Bu endpoint, kullanıcının erişebildiği mağazaların `id` ve `name` alanlarını döner.

## 9. Bildirim Ayarını Okuma

### Endpoint

`GET /api/shops/{user_id}/notification-settings/?shop_id=3`

### Response

```json
{
  "shop_id": 3,
  "shop_name": "Merkez Mağaza",
  "notification_time": "01:00:00",
  "notification_push_token_set": true
}
```

## 10. Önerilen Mobil Akışı

1. Kullanıcı login olur ve `access` token alır.
2. Kullanıcının mağazaları `GET /api/users/{user_id}/shops/` ile çekilir.
3. Kullanıcı bir mağaza seçer.
4. Kullanıcı saat seçer ve `POST /api/shops/{user_id}/notification-settings/` ile kaydeder.
5. Cihazdan gelen olaylar `POST /api/entry-exit-record/` ile gönderilir.
6. Sunucu saat kontrolünü yapar ve gerekiyorsa push gönderir.

## 11. Uygulama Notları

- Kayıt gönderirken mümkünse `created_at` değerini cihaz saatine değil, gerçek olay zamanına göre üretin.
- Saat formatını tek tip tutmak için mobil tarafta `HH:MM` göndermeniz yeterlidir.
- Push token kaydı bir kez yapılabilir, ancak token yenilenirse yeniden gönderilmelidir.
- Eğer bildirimler görünmüyorsa önce şu üç şeyi kontrol edin: mağaza saati, push token, `FCM_SERVER_KEY`.

## 12. Kısa Özet

- Bildirim saati mağaza bazında saklanır.
- Mobil ekip saat ayarını ayrı endpoint ile kaydeder.
- Entry/exit kayıtları gönderildiğinde sunucu saati kontrol eder.
- Saat sonrası olaylarda push denemesi yapılır.
- Gerçek push için token ve FCM server key gerekir.
