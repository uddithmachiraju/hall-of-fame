-- KEYS contains the Redis keys passed from Python:
-- KEYS[1] = idempotency key for this event, such as "lb:idem:event-123"
-- KEYS[2] = Redis Stream key used to record accepted events
-- KEYS[3] onward = leaderboard sorted-set keys
--
-- ARGV contains the values passed from Python:
-- ARGV[1]  = idempotency marker TTL, in seconds
-- ARGV[2]  = points to add
-- ARGV[3]  = player ID
-- ARGV[4]  = score scaling factor (shift)
-- ARGV[5]  = maximum allowed raw points
-- ARGV[6]  = maximum bucket value
-- ARGV[7]  = event ID
-- ARGV[8]  = game ID / slug
-- ARGV[9]  = event timestamp as an ISO-formatted string
-- ARGV[10] = JSON string containing the leaderboard keys
--
-- Remaining arguments contain a bucket and expiration for each board:
-- ARGV[11], ARGV[12] = first board's bucket and expiration
-- ARGV[13], ARGV[14] = second board's bucket and expiration
-- ...and so on.


-- look if the event has already been processed by checking the idempotency key.
if not redis.call('SET', KEYS[1], '1', 'NX', 'EX', tonumber(ARGV[1])) then
  return {0}
end


-- Convert the event's points change from an argument string to a number.
local delta = tonumber(ARGV[2])

-- Scaling factor used to pack raw points and a time tie-breaker
-- into one Redis sorted-set score.
local shift = tonumber(ARGV[4])

-- Upper limit on a player's raw points in each leaderboard.
local max_score = tonumber(ARGV[5])

-- Reference value used to turn a smaller bucket into a larger tie-breaker.
local max_bucket = tonumber(ARGV[6])

-- Start the response with 1, indicating that the event was accepted.
-- Each board's updated raw points and rank will be appended to this table.
local out = {1}


-- Process every leaderboard key.
-- Lua indexing starts at 1.
-- Start at 3 because KEYS[1] is the marker and KEYS[2] is the stream.
-- #KEYS gives the number of entries in the KEYS table.
for i = 3, #KEYS do

  -- Find the argument position containing this board's bucket.
  -- Each board contributes two arguments: bucket, then expiration.
  --
  -- i = 3 -> a = 11
  -- i = 4 -> a = 13
  -- i = 5 -> a = 15
  local a = 11 + (i - 3) * 2

  -- Read this board's time bucket.
  local bucket = tonumber(ARGV[a])

  -- Read this board's expiration as an absolute Unix timestamp in seconds.
  local expire_at = tonumber(ARGV[a + 1])

  -- Get this player's current encoded score from this leaderboard.
  -- ZSCORE: retrieve a member's score from a sorted set.
  -- KEYS[i]: the current leaderboard key.
  -- ARGV[3]: the player ID, used as the sorted-set member.
  -- If the player or board does not exist, the result is false-like.
  local current = redis.call('ZSCORE', KEYS[i], ARGV[3])

  -- A player without an existing entry starts with zero raw points.
  local raw = 0

  -- If an existing score was found, decode its raw points.
  -- Divide by shift to remove the scaling.
  -- math.floor removes the fractional portion contributed by the tie-breaker,
  -- provided the encoding's range and precision requirements are satisfied.
  if current then raw = math.floor(tonumber(current) / shift) end

  -- Apply the event's points change to the player's existing raw points.
  local new_raw = raw + delta

  -- Cap raw points at max_score.
  -- This does not impose a lower bound; negative totals are still possible.
  if new_raw > max_score then new_raw = max_score end

  -- Create or update the player's leaderboard entry.
  --
  -- ZADD creates the sorted set if it does not exist.
  -- It adds the player if missing, or replaces that player's score if present.
  -- Other players' entries are not replaced.
  --
  -- Encoded score:
  --   new_raw * shift          -> primary ordering by points
  --   (max_bucket - bucket)    -> secondary ordering by time bucket
  --
  -- For equal raw points, a smaller bucket produces a larger encoded score.
  -- This tie-breaker is replaced on every accepted update.
  redis.call('ZADD', KEYS[i], new_raw * shift + (max_bucket - bucket), ARGV[3])

  -- If a positive expiration timestamp was provided, apply it.
  -- EXPIREAT sets the absolute expiration time of the entire leaderboard key,
  -- not the expiration of this player's individual entry.
  -- If expire_at is not positive, this line leaves any existing TTL unchanged.
  if expire_at > 0 then redis.call('EXPIREAT', KEYS[i], expire_at) end

  -- Append the player's updated raw points to the response.
  -- #out + 1 is the position immediately after its current last element.
  out[#out + 1] = new_raw

  -- Get the player's position with the highest encoded score ranked first.
  -- ZREVRANK returns a zero-based rank: first place is 0.
  -- Add 1 to return a human-facing rank: first place is 1.
  -- Append that rank immediately after this board's raw points.
  out[#out + 1] = redis.call('ZREVRANK', KEYS[i], ARGV[3]) + 1
end


-- Append one event record after all leaderboard updates finish.
--
-- XADD: append an entry to a Redis Stream.
-- KEYS[2]: the stream key.
-- '*': let Redis generate the stream entry ID.
--
-- The remaining arguments are alternating field names and field values.
-- 'boards' stores the JSON string prepared by Python.
-- 'delta' stores the requested change, even if max_score capped its effect.
--
-- The stream entry ID returned by XADD is not saved or returned here.
redis.call('XADD', KEYS[2], '*',
  'event_id', ARGV[7], 'player_id', ARGV[3], 'game_id', ARGV[8],
  'delta', ARGV[2], 'occurred_at', ARGV[9], 'boards', ARGV[10])


-- Return the accumulated response.
--
-- Duplicate event:
--   [0]
--
-- Accepted event:
--   [1, board_1_points, board_1_rank, board_2_points, board_2_rank, ...]
--
-- Board results follow the same order as the leaderboard keys from Python.
return out
