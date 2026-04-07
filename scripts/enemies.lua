-- ============================================
-- Enemy Spawning & AI Logic
-- Demonstrates event-driven entity management.
-- ============================================

local spawn_timer = 0
local SPAWN_INTERVAL = 60  -- ticks between spawns
local enemy_counter = 0

-- React to game start
on_event("game.start", function(event_name)
    log("Wave " .. game.wave .. " starting!")
    spawn_wave()
end)

-- React to entity destruction
on_event("entity.destroy", function(event_name)
    game.enemies_alive = math.max(0, game.enemies_alive - 1)
    game.score = game.score + 10

    if game.enemies_alive <= 0 then
        game.wave = game.wave + 1
        game.max_enemies = game.max_enemies + 2
        log("Wave " .. game.wave .. " begins! Enemies: " .. game.max_enemies)
        emit_event("game.start", { wave = game.wave })
    end
end)

function spawn_wave()
    for i = 1, game.max_enemies do
        enemy_counter = enemy_counter + 1
        local id = "enemy_" .. enemy_counter
        spawn_entity(id, "enemy")

        -- Random position using math functions
        local x = math.random(50, 750)
        local y = math.random(50, 550)
        set_entity_prop(id, "x", x)
        set_entity_prop(id, "y", y)
        set_entity_prop(id, "health", 30 + game.wave * 5)

        game.enemies_alive = game.enemies_alive + 1
    end
    log("Spawned " .. game.max_enemies .. " enemies")
end

function update_enemies(tick, dt)
    -- Simple AI: enemies drift toward player
    local px = get_entity_prop("player", "x") or 400
    local py = get_entity_prop("player", "y") or 300

    -- We'd iterate entities here in a full implementation
    -- This demonstrates the pattern
end
