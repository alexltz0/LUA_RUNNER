-- ============================================
-- LUA_RUNNER — Game Init Script
-- Entry point loaded first by the engine.
-- ============================================

-- Game state
game = {
    score = 0,
    wave = 1,
    enemies_alive = 0,
    max_enemies = 5,
    player_id = nil,
}

function on_init()
    log("=== LUA_RUNNER Game Demo ===")
    log("Initializing game state...")

    -- Spawn the player entity
    game.player_id = spawn_entity("player", "hero")
    set_entity_prop("player", "health", 100)
    set_entity_prop("player", "x", 400)
    set_entity_prop("player", "y", 300)

    log("Player spawned at (400, 300)")
    emit_event("game.start", { wave = game.wave })
end

function on_shutdown()
    log("Game shutting down. Final score: " .. game.score)
end
