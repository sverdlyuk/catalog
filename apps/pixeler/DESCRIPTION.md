# Pixeler для Lilka v2

Альтернативна прошивка для плати Lilka v2 на основі фреймворку Pixeler. 

Alternative firmware for the Lilka v2 board based on the Pixeler framework.

## Особливості

Прошивка збирається плагіном `Pioarduino` та не може бути зібрана з допомогою `Platformio`. 

Готові до завантаження на плату двійкові файли прошивки знаходяться в каталозі `pixeler4lilkav2\bin\parts`.

Для завантаження прошивки з `Keira OS`, зкопіюйте на карту пам'яті файл `firmware.bin` та завантажте його.

Для встановлення прошивки без відкату в `Keira OS`, завантажте на плату файл `pixeler.bin` з допомогою утиліти `esptool`.

## Документація

Документація фреймворку заходиться в каталозі `pixeler4lilkav2\src\pixeler\doc`. 
Її можна зібрати та запустити локально, виконавши кроки з Readme.
