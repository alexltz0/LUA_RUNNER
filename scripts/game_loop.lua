-- ============================================
-- Main Game Loop (on_tick)
-- Called every engine tick. Orchestrates all
-- per-frame game logic.
-- ============================================

local combat_timer = 0
local COMBAT_TICK = 90     -- auto-combat every 90 ticks
local status_timer = 0
local STATUS_TICK = 180    -- status report every 180 ticks

function on_tick(tick, dt)
    -- Auto-combat simulation
    combat_timer = combat_timer + 1
    if combat_timer >= COMBAT_TICK then
        combat_timer = 0
        auto_combat(tick)
    end

    -- Periodic status report
    status_timer = status_timer + 1
    if status_timer >= STATUS_TICK then
        status_timer = 0
        print_status(tick)
    end
end

function auto_combat(tick)
    -- Simulate combat: pick a random enemy to damage
    if game.enemies_alive > 0 then
        -- Find an active enemy (simplified)
        for i = 1, 100 do
            local id = "enemy_" .. i
            local hp = get_entity_prop(id, "health")
            if hp and hp > 0 then
                local dmg = math.random(10, 25)
                deal_damage(id, dmg)
                break
            end
        end
    end
end

function print_status(tick)
    log("--- Status @ tick " .. tick .. " ---")
    log("  Score: " .. game.score)
    log("  Wave: " .. game.wave)
    log("  Enemies alive: " .. game.enemies_alive)
    local player_hp = get_entity_prop("player", "health") or 0
    log("  Player HP: " .. player_hp)
    log("-------------------------------")
end
