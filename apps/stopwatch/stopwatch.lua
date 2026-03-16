--[[
    Секундомір для Lilka
    Кнопки:
      A    - Старт / Стоп
      B    - Вихід
      D    - Коло (коли запущено) / На нуль (коли зупинено)
      C    - Налаштування (лише візуальна)
      UP   - прокрутити кола вгору
      DOWN - прокрутити кола вниз
]]

-- ========================
-- Кольори
-- ========================
local BLACK  = display.color565(0,   0,   0)
local WHITE  = display.color565(255, 255, 255)
local GREEN  = display.color565(0,   200, 80)
local GRAY   = display.color565(120, 120, 120)
local YELLOW = display.color565(255, 220, 0)

-- ========================
-- Стан програми
-- ========================
local running    = false   -- чи запущено секундомір
local elapsed    = 0.0     -- загальний час у секундах
local lap_start  = 0.0     -- час початку поточного кола
local laps       = {}      -- усі збережені кола
local lap_count  = 0       -- лічильник кіл
local scroll     = 0       -- індекс першого видимого кола

local VISIBLE    = 4       -- скільки кіл видно одночасно

-- ========================
-- Допоміжна: форматує секунди у MM:SS.mm
-- ========================
local function format_time(t)
    local m  = math.floor(t / 60)
    local s  = math.floor(t % 60)
    local ms = math.floor((t * 100) % 100)
    return string.format("%02d:%02d.%02d", m, s, ms)
end

-- ========================
-- Допоміжна: малює кнопку у стилі ігрової консолі
-- Аргументи: cx, cy - центр кружечка, label - буква, text - підпис
-- ========================
local function draw_button(cx, cy, label, text)
    display.fill_circle(cx, cy, 10, GREEN)
    display.set_text_color(BLACK)
    display.set_font("9x15")
    display.set_cursor(cx - 3, cy + 5)
    display.print(label)
    display.set_text_color(WHITE)
    display.set_cursor(cx + 14, cy + 5)
    display.print(text)
end

-- ========================
-- lilka.update: логіка (викликається ~30 разів/сек)
-- ========================
function lilka.update(delta)
    local btn = controller.get_state()

    -- Кнопка A: запуск або зупинка
    if btn.a.just_pressed then
        running = not running
    end

    -- Кнопка B: вихід з програми
    if btn.b.just_pressed then
        util.exit()
    end

    -- Кнопка D: коло або скидання на нуль
    if btn.d.just_pressed then
        if running then
            -- Зберігаємо поточне коло
            local lap_time = elapsed - lap_start
            lap_count = lap_count + 1
            table.insert(laps, { n = lap_count, lap = lap_time, total = elapsed })
            lap_start = elapsed
            -- Автоматично скролимо до останнього кола
            if #laps > VISIBLE then
                scroll = #laps - VISIBLE
            end
        else
            -- Скидаємо все на нуль
            elapsed   = 0.0
            lap_start = 0.0
            laps      = {}
            lap_count = 0
            scroll    = 0
        end
    end

    -- UP/DOWN: скролінг кіл
    if btn.up.just_pressed then
        if scroll > 0 then
            scroll = scroll - 1
        end
    end
    if btn.down.just_pressed then
        if scroll < #laps - VISIBLE then
            scroll = scroll + 1
        end
    end

    -- Збільшуємо час, якщо секундомір запущено
    if running then
        elapsed = elapsed + delta
    end
end

-- ========================
-- lilka.draw: малювання кадру
-- ========================
function lilka.draw()
    local W = display.width   -- 280
    local H = display.height  -- 240

    -- Очищаємо екран
    display.fill_screen(BLACK)

    -- --- Великі цифри секундоміру по центру ---
    display.set_font("10x20")
    display.set_text_size(3)
    display.set_text_color(WHITE)
    local time_str = format_time(elapsed)
    local tx = (W - 240) / 2
    local ty = H / 2 - 35
    display.set_cursor(tx, ty)
    display.print(time_str)
    display.set_text_size(1)

    -- --- Кола під таймером ---
    display.set_font("8x13")
    local laps_y = ty + 25   -- вертикаль всього блоку
    local col1_x = 40        -- колонка: номер кола
    local col2_x = 90        -- колонка: час кола
    local col3_x = 180       -- колонка: загальний час

    -- заголовки колонок
    display.set_text_color(GRAY)
    display.set_cursor(col1_x, laps_y)
    display.print("Коло")
    display.set_cursor(col2_x, laps_y)
    display.print("Час кола")
    display.set_cursor(col3_x, laps_y)
    display.print("Загальний")

    -- рядки кіл (показуємо VISIBLE штук починаючи з scroll)
    display.set_text_color(YELLOW)
    for i = 1, VISIBLE do
        local idx = scroll + i       -- індекс у таблиці laps
        local lap = laps[idx]
        if lap then
            local y = laps_y + 14 + (i - 1) * 14
            display.set_cursor(col1_x, y)
            display.print(string.format("#%d", lap.n))
            display.set_cursor(col2_x, y)
            display.print(format_time(lap.lap))
            display.set_cursor(col3_x, y)
            display.print(format_time(lap.total))
        end
    end

    -- --- Підвал (footer) з кнопками ---
    local footer_y = H - 48

    -- Ліворуч: A (Старт/Стоп) та B (Вихід)
    local a_label = running and "Стоп" or "Старт"
    draw_button(30, footer_y,      "A", a_label)
    draw_button(30, footer_y + 28, "B", "Вихід")

    -- Праворуч: D (Коло/На нуль) та C (Налаштування)
    local d_label = running and "Коло" or "На нуль"
    draw_button(W - 90, footer_y,      "D", d_label)
end