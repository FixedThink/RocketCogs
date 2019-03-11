# Default library.
import datetime
import sqlite3  # Only to make the db on init.

# Requirements.
import aiosqlite


class DbQueries:
    """Query the account registrations"""
    CREATE_TABLE = "CREATE TABLE `registrations` (`userID` INTEGER, `username` TEXT, `timestamp` TEXT, " \
                   "`platform` INTEGER, `gamer_id` TEXT, PRIMARY KEY(`userID`));"
    TABLE_CHECK = "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='registrations';"
    DELETE_LINK = "DELETE FROM `registrations` WHERE userID = ?"
    INSERT_LINK = "INSERT OR REPLACE INTO `registrations` VALUES (?, ?, ?, ?, ?);"
    SELECT_LINK = "SELECT `platform`, `gamer_id` FROM `registrations` WHERE userID = ?"

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
            print("Making the registrations table...")
            cursor.execute(self.CREATE_TABLE)
            connection.commit()
        connection.close()
        return

    # Query methods.
    async def delete_user(self, user_id) -> None:
        """Delete the link information for a user"""
        await self.exec_sql(self.DELETE_LINK, [user_id], commit=True)
        return

    async def insert_user(self, user_id, username, platform, gamer_id) -> None:
        """Insert the link information for a user"""
        stamp = str(datetime.datetime.utcnow())
        await self.exec_sql(self.INSERT_LINK, [user_id, username, stamp, platform, gamer_id], commit=True)
        return

    async def select_user(self, user_id) -> tuple:
        """Get the platform and gamer_id of a user in the DB. Returns (False, False) if there's no match"""
        resp = await self.exec_sql(self.SELECT_LINK, [user_id])
        if len(resp) == 0:  # No match
            platform, gamer_id = (None, None)
        else:
            platform, gamer_id = resp[0]
        return platform, gamer_id

    # Utilities.
    async def exec_sql(self, query, params=None, commit=False) -> list:
        """Make an SQL query to the userID - gamer ID Database"""
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(query, parameters=params) as cursor:
                rows = await cursor.fetchall()
            if commit:
                await db.commit()
        return rows
