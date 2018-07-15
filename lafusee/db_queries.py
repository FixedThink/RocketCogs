# Default library.
import datetime

# Requirements.
import aiosqlite


class DbQueries:
    """Query the account registrations asynchronically"""
    CREATE_TABLE = "CREATE TABLE `registrations` (`userID` INTEGER UNIQUE, `username` TEXT, `timestamp` TEXT," \
                   "`platform` INTEGER, `gamer_id` TEXT);"
    TABLE_CHECK = "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=registrations;"
    DELETE_LINK = "DELETE FROM `registrations` WHERE userID = ?"
    INSERT_LINK = "INSERT OR REPLACE INTO `registrations` VALUES (?, ?, ?, ?, ?);"
    SELECT_LINK = "SELECT `platform`, `gamer_id` FROM `registrations` WHERE userID = ?"

    def __init__(self, db_path):
        self.path = db_path

    # Query methods.
    async def delete_user(self, userid) -> None:
        """Delete the link information for a user"""
        await self.exec_sql(self.DELETE_LINK, [userid], commit=True)
        return

    async def insert_user(self, userid, username, platform, gamer_id) -> None:
        """Insert the link information for a user"""
        await self.check_table()
        stamp = str(datetime.datetime.utcnow())
        await self.exec_sql(self.INSERT_LINK, [userid, username, stamp, platform, gamer_id], commit=True)
        return

    async def select_user(self, userid) -> tuple:
        """Get the platform and gamer_id of a user in the DB. Returns (False, False) if there's no match"""
        await self.check_table()
        resp = await self.exec_sql(self.SELECT_LINK, [userid])
        if len(resp) == 0:  # No match
            platform, gamer_id = (False, False)
        else:
            platform, gamer_id = resp[0]
        return platform, gamer_id

    # Utilities.
    async def check_table(self) -> None:
        """Check if the table exists. If not, create it."""
        resp = await self.exec_sql(self.TABLE_CHECK)
        is_table = bool(resp[0][0])
        if is_table is False:
            print("Making the registrations table...")
            await self.exec_sql(self.CREATE_TABLE)
        return

    async def exec_sql(self, query, params=None, commit=False) -> tuple:
        """Make an SQL query to the ESC Database"""
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(query, parameters=params) as cursor:
                rows = await cursor.fetchall()
            if commit:
                await db.commit()
        return rows
