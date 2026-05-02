# Mağaza Bildirim Saatleri — Kısa Kılavuz

Bu belge yalnızca yeni eklenen "mağaza bildirim saati" özelliğine odaklanır: mobil uygulamanın mağaza için saat ve cihaz token'ı kaydetmesi ve sunucunun kayıt geldiğinde bildirim tetiklemesi.

Özet
- Model: `Shop.notification_time` (TimeField), `Shop.notification_push_token` (TextField).
- Önemli endpointler:
  - `POST /api/shops/<user_id>/notification-settings/` — mağaza için saat ve (opsiyonel) push token kaydetme.
  - `GET  /api/shops/<user_id>/notification-settings/?shop_id=<shop_id>` — mevcut ayarları alma.
  - Kayıt endpointleri (ölçüm/giriş-çıkış): `POST /api/records/add/` veya `POST /api/entry-exit-record/` — sunucu burada gelen kaydı işler ve bildirim tetikler.

1) Yetkilendirme
- `notification-settings` endpoint'i için kullanıcı `user_id` ile doğrulanır; mobil uygulama önce API üzerinden login (JWT) olmalıdır.

2) Mağaza için saat ve token kaydetme (mobilin yapacağı)

- Endpoint: `POST /api/shops/<user_id>/notification-settings/`
- İçerik-type: `application/json`
- Body örneği:

```
{
  "shop_id": 123,
  "notification_time": "01:00",        // veya "01:00:00"
  "push_token": "<FCM_OR_APNS_TOKEN>"  // opsiyonel ama önerilir
}
```

- Notlar:
  - `notification_time` 24 saat formatında `HH:MM` veya `HH:MM:SS` olmalıdır.
  - `push_token` mobil cihazdan alınan FCM/APNs token'ıdır; sunucuda bu token yoksa bildirim gönderilemez.

3) Sunucu davranışı — kayıt geldiğinde bildirim kontrolü

- Kayıt endpoint'ine gelen her kayıt için (`created_at` zorunlu):
  - `created_at` parse edilir (format: `YYYY-MM-DD HH:MM:SS`).
  - Eğer ilgili `Shop.notification_time` doluysa ve `created_at.time() >= notification_time` ise, sunucu push göndermeyi dener (giriş/çıkış ise).

4) Push gereksinimleri
- Sunucu FCM kullanır; çalışması için `FCM_SERVER_KEY` ayarlı olmalıdır.
- Mobil uygulama `push_token`'ı kaydetmek zorunda değildir. Sunucu token yoksa otomatik olarak mağazaya özel topic'e yollar: `/topics/shop_<shop_id>`.
- Mobil uygulama bu topic'e FCM SDK ile abone olmalıdır. Örneğin `shop_2` mağazası için cihaz `shop_2` topic'ine subscribe edilmelidir.
- Eğer uygulama topic'e abone olmazsa test bildirimi de dahil hiçbir push alınmaz.

Bu projede backend tarafı artık hem gerçek kayıtlar için hem de test için topic tabanlı gönderimi otomatik kullanır; mobilin sunucuya ayrıca token göndermesi gerekmez.

5) Örnek cURL — mağaza için saat ve token kaydetme

```bash
curl -X POST "https://<host>/api/shops/45/notification-settings/" \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"shop_id":12, "notification_time":"01:00", "push_token":"<FCM_TOKEN>"}'
```

Başarılı response (örnek):

```json
{
  "message": "Bildirim saati kaydedildi.",
  "shop_id": 12,
  "shop_name": "Mağaza X",
  "notification_time": "01:00:00",
  "notification_push_token_set": true
}
```

6) Örnek cURL — cihazdan kayıt gönderme

```bash
curl -X POST "https://<host>/api/records/add/" \
  -H "Content-Type: application/json" \
  -d '[{"shopid":12, "deviceid":10, "isentry":true, "isexit":false, "rssi":-55, "created_at":"2026-05-01 01:12:34"}]'
```

Sunucu bu kaydı işler; eğer `notification_time` 01:00 ise ve `created_at` 01:12 ise push gönderilmeye çalışılır.

7) Timezone ve format uyarısı
- Mevcut implementasyon `created_at`'ı `YYYY-MM-DD HH:MM:SS` olarak bekler ve timezone-aware değildir. Mobil ekip, sunucu saat dilimine uygun zaman (ör. Türkiye UTC+3) göndermeli veya UTC tercih edilecekse backend ile koordinasyon yapmalıdır.

8) Test adımları
- Mobil uygulamada test token alın.
- `POST /api/shops/<user_id>/notification-settings/` ile `notification_time` ve `push_token` kaydedin.
- `POST /api/records/add/` ile `created_at` değeri `notification_time` sonrası olacak şekilde kayıt gönderin.
- Sunucu loglarında bildirim denemesini kontrol edin.

9) Limitasyonlar
- Tek token tutuluyor (çoklu cihazlar için genişletme gerekebilir).
- FCM anahtarı yoksa push atılamaz.

10) Backend test komutu
- Shop ID 2 için artık her 1 dakikada bir sahte giriş/çıkış kaydı oluşturuluyor ve aynı anda test bildirimi gönderiliyor.
- Vercel üzerinde bu iş otomatik cron ile çalışır; deploy sonrası manuel worker açmanız gerekmez.
- Lokal test veya alternatif ortam için aynı işi şu komut yapar:

```bash
/Users/furkancanisci/Desktop/entry_project/venv/bin/python manage.py fake_entries_and_notify --shop-id 2 --interval 60
```

- `Procfile` içindeki worker yerel/alternatif çalıştırmalar içindir; Vercel tarafında cron endpoint bunu otomatik tetikler.

- Tek seferlik test için:

```bash
/Users/furkancanisci/Desktop/entry_project/venv/bin/python manage.py fake_entries_and_notify --shop-id 2 --once
```

- Bu komut FCM topic hedefi kullanır: `shop_2`. Mobil uygulamanın bu topic'e abone olması gerekir; token sunucuya gönderilmek zorunda değildir.

11) Mobil ekibin yapması gereken yeni şeyler
- Uygulama açıldığında veya mağaza seçildiğinde ilgili topic'e subscribe olun: örneğin shop 2 için `shop_2`.
- Bildirim iznini istemeyi unutmayın; kullanıcı izni kapalıysa push görünmez.
- Test akışında gerçek cihaz/emu üzerinde uygulamanın arka planda da bildirim alabildiğini doğrulayın.
- Eğer birden fazla mağaza varsa, kullanıcı hangi mağazayı seçerse o mağazanın topic'ine geçin; eski topic aboneliğini bırakmak iyi olur.
- Test push'lar artık backend cron'u ile otomatik geldiği için ayrıca bir mobil test butonuna ihtiyaç yok.

Dosya referansları:
- `entryapp/models.py`, `entryapp/views.py`, `entryapp/templates/entryapp/shops.html`
- `entryapp/management/commands/send_shop_test_notification.py`

-- Son
