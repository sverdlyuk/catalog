# ESPHome LVGL для Lilka (в процесі)

ESPHome конфігурація для Lilka на базі ESP32-S3 з підтримкою графічного фреймворку LVGL (LittlevGL).

![IMG_2284](https://github.com/user-attachments/assets/330f7477-2f81-4e32-b60c-75d941f841c9)

---

## Можливості

* **Графічний Інтерфейс (LVGL):**
    * ✅ Підтримка дисплея ST7789V (280x240, SPI).
    * ✅ Інтеграція [LVGL](https://esphome.io/components/lvgl/) для створення інтерактивного інтерфейсу.
    * ✅ [Flex Layout](https://esphome.io/cookbook/lvgl/#flex-layout-positioning) для адаптивного розташування елементів.
    * ✅ Динамічне відображення стану бойлера (Home Assistant Switch).
    * ✅ Відображення рівня заряду та напруги батареї з автооновленням.
    * ✅ I2S Audio Speaker: Підтримка відтворення аудіо (наприклад, голосових оголошень, або медіа через Home Assistant).

## Основні Мережеві Функції ESPHome

* **OTA (Over-The-Air):** Дозволяє оновлювати прошивку пристрою бездротово через Wi-Fi після першого підключення.
* **Web Server:** Надає веб-інтерфейс (зазвичай на порту 80) для моніторингу статусу, перегляду логів та базового керування пристроєм через браузер.
* **Captive Portal:** Створює аварійну Wi-Fi точку доступу для введення нових облікових даних мережі, якщо пристрій не може підключитися.
* **mDNS (Multicast DNS):** Дозволяє знаходити пристрій у локальній мережі за зрозумілим іменем (`lilka.local`), а не лише за IP-адресою.
* **Native API:** Встановлює швидкий, зашифрований та оптимізований двосторонній зв'язок для інтеграції з Home Assistant.
* **BLE Tracker:** Активує модуль **Bluetooth Low Energy** для сканування та відстеження навколишніх BLE-пристроїв.
* **Bluetooth Proxy:** Передає дані, зібрані BLE Tracker, до Home Assistant, розширюючи покриття мережі розумного будинку.

<img width="1210" height="921" alt="Знімок екрана 2025-12-03 о 01 34 48" src="https://github.com/user-attachments/assets/78734ebe-4c78-4178-9d95-547932706a6e" />


## Керування пристроями Home Assistant (HA)

* **Двосторонній Зв'язок:** ESPHome може отримувати статус та [керувати пристроями](https://esphome.io/components/sensor/homeassistant/) Home Assistant.
* **Налаштування HA:** Для роботи функції керування в інтеграції ESPHome у Home Assistant потрібно увімкнути опцію "Enable the API to allow the ESP device to register and control entities in Home Assistant." [Демо відео](https://youtu.be/4dKZSFFEjWA), [Демо 2](https://youtu.be/m2ZnhPG_efg)

## Схема виводів GPIO

| Pin | Function |
|-----|----------|
| 46  | Display power (GPIO output) |
| 1   | I2S LRCLK for speaker |
| 42  | I2S BCLK for speaker |
| 2   | I2S DOUT — audio output |
| 3   | ADC input for battery voltage |
| 18  | SPI CLK for display |
| 17  | SPI MOSI for display |
| 15  | ST7789 DC |
| 7   | ST7789 CS |
| 38  | Button Up |
| 41  | Button Down |
| 39  | Button Left |
| 40  | Button Right |
| 5   | Button A |
| 6   | Button B |
| 10  | Button C |
| 9   | Button D |
| 4   | Button Start |
| 0   | Button Select |


### Апаратне забезпечення

- **Платформа**: ESP32-S3 DevKitC-1
- **Дисплей**: ST7789V (SPI)
  - DC: GPIO15
  - CS: GPIO7
  - CLK: GPIO18
  - MOSI: GPIO17
- **Живлення дисплея**: GPIO46
- **Батарея**: ADC GPIO3 (з множником 1.33)


## Встановлення

1. Встановіть [ESPHome](https://esphome.io/)
2. Створіть файл `lilka.yaml` з конфігурацією
3. Налаштуйте WiFi credentials у `secrets.yaml`:
   ```yaml
   wifi_ssid: "YourWiFiName"
   wifi_password: "YourWiFiPassword"
   ```
4. Завантажте прошивку: `esphome run lilka.yaml`

## Конфігурація

Повна конфігурація доступна на [GitHub](https://github.com/sverdlyuk/Lilka-ESPHome)

## Статус розробки

⚠️ **В процесі розробки** - 
## Автор
Свердлюк (sverdlyuk)
