from __future__ import annotations

from datetime import datetime, timedelta, timezone

LEASE_RENEW_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  redis.call('PEXPIRE', KEYS[1], ARGV[2])
  return 1
end
return 0
"""

LEASE_RELEASE_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
"""

TERMINALIZATION_CLAIM_SCRIPT = """
local existing_status = redis.call('HGET', KEYS[1], 'status')
local existing_attempts = redis.call('HGET', KEYS[1], 'attempts')
local existing_worker_id = redis.call('HGET', KEYS[1], 'worker_id')
local existing_completed_at = redis.call('HGET', KEYS[1], 'completed_at')
local existing_notification_id = redis.call('HGET', KEYS[1], 'notification_id')
local existing_terminal_event_id = redis.call('HGET', KEYS[1], 'terminal_event_id')

if existing_status == 'done' or existing_status == 'failed' then
  if existing_status == ARGV[1] then
    if existing_terminal_event_id and existing_terminal_event_id ~= '' then
      return {
        'duplicate',
        existing_status,
        existing_attempts or '',
        existing_worker_id or '',
        existing_completed_at or '',
        existing_notification_id or '',
        existing_terminal_event_id
      }
    end

    return {
      'accepted_pending',
      existing_status,
      existing_attempts or '',
      existing_worker_id or '',
      existing_completed_at or '',
      existing_notification_id or '',
      ''
    }
  end

  return {
    'conflict',
    existing_status,
    existing_attempts or '',
    existing_worker_id or '',
    existing_completed_at or '',
    existing_notification_id or '',
    existing_terminal_event_id or ''
  }
end

redis.call(
  'HSET',
  KEYS[1],
  'status',
  ARGV[1],
  'attempts',
  ARGV[2],
  'worker_id',
  ARGV[3],
  'updated_at',
  ARGV[4],
  'completed_at',
  ARGV[4],
  'notification_id',
  ARGV[5]
)
redis.call('HDEL', KEYS[1], 'terminal_event_id', 'leased_until', 'heartbeat_at')

return {
  'accepted_new',
  ARGV[1],
  ARGV[2],
  ARGV[3],
  ARGV[4],
  ARGV[5],
  ''
}
"""


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def utc_isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def parse_utc_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def lease_until(from_dt: datetime, lease_seconds: int) -> datetime:
    return from_dt + timedelta(seconds=lease_seconds)


def lease_ttl_ms(lease_seconds: int) -> int:
    return lease_seconds * 1000


__all__ = [
    "LEASE_RELEASE_SCRIPT",
    "LEASE_RENEW_SCRIPT",
    "TERMINALIZATION_CLAIM_SCRIPT",
    "lease_ttl_ms",
    "lease_until",
    "now_utc",
    "parse_utc_datetime",
    "utc_isoformat",
]
