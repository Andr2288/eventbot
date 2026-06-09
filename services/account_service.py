"""Небезпечні операції з акаунтом."""

import db.event_repo as event_repo
import db.reminder_repo as reminder_repo
import db.user_repo as user_repo


async def delete_all_events(user_id: int) -> int:
    return await event_repo.delete_all_events(user_id)


async def clear_all_reminders(user_id: int) -> int:
    return await reminder_repo.delete_all_reminders(user_id)


async def delete_account(user_id: int) -> bool:
    await reminder_repo.delete_all_reminders(user_id)
    await event_repo.delete_all_events(user_id)
    return await user_repo.delete_user(user_id)
