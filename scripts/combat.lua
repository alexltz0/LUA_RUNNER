-- ============================================
-- Combat System
-- Demonstrates damage events, health tracking,
-- and event-driven game logic.
-- ============================================

-- Listen for damage events
on_event("combat.damage", function(event_name)
    log("Damage event fired")
end)

-- Apply damage to an entity
function deal_damage(target_id, amount)
    local health = get_entity_prop(target_id, "health")
    if health == nil then
        log_warn("Cannot damage " .. target_id .. ": not found")
        return
    end

    local new_health = math.max(0, health - amount)
    set_entity_prop(target_id, "health", new_health)

    emit_event("combat.damage", {
        target = target_id,
        amount = amount,
        remaining = new_health,
    })

    log(target_id .. " took " .. amount .. " damage (" .. new_health .. " HP remaining)")

    if new_health <= 0 then
        log(target_id .. " destroyed!")
        emit_event("combat.kill", { target = target_id })
        destroy_entity(target_id)
    end
end

-- Heal an entity
function heal_entity(target_id, amount)
    local health = get_entity_prop(target_id, "health")
    if health == nil then return end

    local max_health = 100
    local new_health = math.min(max_health, health + amount)
    set_entity_prop(target_id, "health", new_health)

    emit_event("combat.heal", {
        target = target_id,
        amount = amount,
        resulting = new_health,
    })

    log(target_id .. " healed for " .. amount .. " (" .. new_health .. " HP)")
end
