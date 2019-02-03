# Default library.
import datetime as dt
import sqlite3  # Only to make the db on init.
from typing import Optional

# Requirements.
import aiosqlite


class DbQueries:
    """Query the reputation database"""
    CREATE_TABLE = "CREATE TABLE `reputations` (`from_user` INTEGER, `from_name` TEXT, `to_user` INTEGER, " \
                   "`to_name` TEXT, `stamp` TEXT, `message` TEXT);"
    TABLE_CHECK = "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='reputations';"
    INSERT_REP = "INSERT OR REPLACE INTO `reputations` VALUES (?, ?, ?, ?, ?, ?);"
    SELECT_REP_PAIR = "SELECT * from reputations WHERE from_user = ? AND to_user = ? AND stamp > ?"
    SELECT_REP_COUNT = "SELECT COUNT(*) as repCount FROM reputations WHERE to_user = ?;"
    SELECT_LEADERBOARD = "SELECT to_user, COUNT(to_user) as rep_count FROM reputations " \
                         "GROUP BY to_user ORDER BY rep_count desc;"

    def __init__(self, db_path):
        self.path = db_path
        self.init_table()

    def init_table(self) -> None:
        """Check if the table exists. If not, create it.

        Note: this method uses sqlite3 rather than aiosqlite"""
        connection = sqlite3.connect(self.path)
        cursor = connection.cursor()
        cursor.execute(self.TABLE_CHECK)
        resp = cursor.fetchall()
        is_table = bool(resp[0][0])
        if is_table is False:
            print("Making the reputations table...")
            cursor.execute(self.CREATE_TABLE)
            connection.commit()
        connection.close()
        return

    async def insert_rep(self, from_id, from_name, to_id, to_name, rep_msg, cooldown: int = None) -> bool:
        """
        :param from_id: UserID of the user that gives the rep.
        :param from_name: username#1234 of the user that gives the rep.
        :param to_id: UserID of the user that is being rep'd.
        :param to_name: username#1234 of the user that is being rep'd.
        :param rep_msg: The message accompanied with the rep.
        :param cooldown: (Optional) The amount of seconds that need to have passed since the last time
               from_id rep'd to_id.
        :return:
        """
        if cooldown:  # TODO: Test!
            compare_stamp = dt.datetime.utcnow() - dt.timedelta(seconds=cooldown)
            check_rows = await self.exec_sql(self.SELECT_REP_PAIR, [from_id, to_id, compare_stamp])
            can_insert = not check_rows  # Boolean, if check_rows is empty then the rep can be inserted.
        else:
            can_insert = True
        if can_insert:
            stamp = str(dt.datetime.utcnow())
            await self.exec_sql(self.INSERT_REP, [from_id, from_name, to_id, to_name, stamp, rep_msg], commit=True)
        return can_insert

    async def user_rep_count(self, user_id: int) -> Optional[int]:
        """
        :param user_id: The userID of the user whose reputation count should be checked.
        :return: The amount of reputations received by the user.
        """
        resp = await self.exec_sql(self.SELECT_REP_COUNT, params=[user_id])
        return resp[0][0] if resp else None

    # Utilities.
    async def exec_sql(self, query, params=None, commit=False) -> tuple:
        """Make an asynchronous query to the reputation database"""
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(query, parameters=params) as cursor:
                rows = await cursor.fetchall()
            if commit:
                await db.commit()
        return rows
