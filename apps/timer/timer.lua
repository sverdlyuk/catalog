--[[
    Таймер для Lilka
    LEFT/RIGHT - поле  |  UP/DOWN - значення  |  A - старт/пауза  |  B - вихід
]]

local BLACK  = display.color565(0, 0, 0)
local WHITE  = display.color565(255, 255, 255)
local YELLOW = display.color565(255, 220, 0)
local GREEN  = display.color565(0, 200, 80)
local GRAY   = display.color565(120, 120, 120)

local fields    = {0, 0, 0}    -- години, хвилини, секунди
local max_val   = {99, 59, 59}
local cursor    = 1
local running   = false
local finished  = false
local remaining = 0.0

local finish_melody = {
    {notes.C5, 8}, {notes.E5, 8}, {notes.G5, 8}, {notes.C6, 4},
    {0, 8},
    {notes.G5, 8}, {notes.A5, 8}, {notes.B5, 8}, {notes.C6, 4},
    {0, 8},
    {notes.E5, 8}, {notes.G5, 8}, {notes.C6, 8}, {notes.E6, -4},
    {0, 4},
    {notes.C6, 4}, {notes.G5, 4}, {notes.E5, 2},
}

local function total_secs()
    return fields[1] * 3600 + fields[2] * 60 + fields[3]
end

function lilka.update(delta)
    local btn = controller.get_state()

    if btn.b.just_pressed then util.exit() end

    if finished then
        if btn.a.just_pressed then
            finished = false; fields = {0,0,0}; remaining = 0; cursor = 1
            buzzer.stop()
        end
        return
    end

    if btn.a.just_pressed then
        if running then
            running = false
        elseif total_secs() > 0 then
            if remaining <= 0 then remaining = total_secs() end
            running = true
        end
    end

    if not running then
        if btn.left.just_pressed  then cursor = cursor == 1 and 3 or cursor - 1 end
        if btn.right.just_pressed then cursor = cursor == 3 and 1 or cursor + 1 end
        if btn.up.just_pressed then
            fields[cursor] = (fields[cursor] + 1) % (max_val[cursor] + 1)
            remaining = 0
        end
        if btn.down.just_pressed then
            fields[cursor] = (fields[cursor] - 1 + max_val[cursor] + 1) % (max_val[cursor] + 1)
            remaining = 0
        end
    end

    if running then
        remaining = remaining - delta
        if remaining <= 0 then
            remaining = 0; running = false; finished = true
            buzzer.play_melody(finish_melody, 200)
        end
    end
end

function lilka.draw()
    local W, H = display.width, display.height
    display.fill_screen(BLACK)

    -- Цифри
    local dh, dm, ds
    if running or finished then
        local t = math.floor(remaining)
        dh = math.floor(t/3600); dm = math.floor(t%3600/60); ds = t%60
    else
        dh, dm, ds = fields[1], fields[2], fields[3]
    end

    display.set_font("10x20")
    display.set_text_size(3)
    display.set_text_color(WHITE)
    display.set_cursor(W/2 - 120, H/2 - 25)
    display.print(string.format("%02d:%02d:%02d", dh, dm, ds))
    display.set_text_size(1)

    -- Підкреслення активного поля
    if not running and not finished then
        local offsets = {W/2 - 120, W/2 - 120 + 90, W/2 - 120 + 180}
        display.fill_rect(offsets[cursor], H/2 + 16, 60, 3, YELLOW)
    end

    -- Footer: B зліва, A з підписом справа
    local a_label
    if finished then
        a_label = "A: скинути"
    elseif running then
        a_label = "A: стоп"
    else
        a_label = "A: старт"
    end

    display.set_font("10x20")
    display.set_text_color(GRAY)
    display.set_cursor(8, H - 16)
    display.print("B: вихід")
    display.set_text_color(GREEN)
    display.set_cursor(W - (#a_label * 8), H - 16)
    display.print(a_label)
end
