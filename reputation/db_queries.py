# Default library.
import datetime as dt
import sqlite3  # Only to make the db on init.
from typing import List, Optional, Tuple, Set

# Requirements.
import aiosqlite


# TODO: some todo about typehints that #s will take care of.
class DbQueries:
    """Query the reputation database"""
    CREATE_TABLE = "CREATE TABLE `reputations` (`from_user` INTEGER, `from_name` TEXT, `to_user` INTEGER, " \
                   "`to_name` TEXT, `stamp` TEXT, `message` TEXT);"
    CREATE_INDEX = "CREATE INDEX get_users_reps ON reputations(to_user);"
    TABLE_CHECK = "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='reputations';"
    INSERT_REP = "INSERT OR REPLACE INTO `reputations` VALUES (:f_id, :f_n, :t_id, :t_n, :stamp, :msg);"
    SELECT_REP_PAIR = "SELECT * from reputations WHERE from_user = ? AND to_user = ? AND stamp > ?"
    SELECT_REP_COUNT = "SELECT COUNT(*) as rep_count, COUNT(DISTINCT from_user) as u_count, " \
                       "MAX(stamp) as most_recent FROM reputations WHERE to_user = ?;"
    SELECT_LEADERBOARD = "SELECT to_user, COUNT(to_user) as rep_count FROM reputations " \
                         "GROUP BY to_user ORDER BY rep_count DESC, MAX(stamp) DESC;"
    CHECK_SIMPLE = "SELECT to_user from reputations GROUP BY to_user HAVING COUNT(*) >= ?;"
    CHECK_DOUBLE = "SELECT to_user from reputations WHERE stamp > ? GROUP BY to_user HAVING COUNT(*) >= ?\n" \
                   "INTERSECT\n" + CHECK_SIMPLE
    GET_RECENT_REPS = "SELECT COUNT(*) from reputations WHERE to_user = ? AND stamp > ?"

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
            cursor.execute(self.CREATE_INDEX)  # To ensure quick rep lookup.
            connection.commit()
        connection.close()
        return

    async def all_eligible_users(self, decay_threshold: int, role_threshold: int,
                                 decay_period: Optional[int]) -> Set[int]:
        """
        :param decay_threshold: The minimum amount of reps a user must receive within decay_period to keep the role.
        :param role_threshold: The minimum amount of reps a user needs to receive the reputation role.
        :param decay_period: The time period in which a user must receive decay_threshold reps to keep the role.
        :return: A list of all user ids who are eligible for the reputation role.
        """
        if decay_period:
            stamp = dt.datetime.utcnow() - dt.timedelta(seconds=decay_period)
            id_list = await self.exec_sql(self.CHECK_DOUBLE, params=[stamp, decay_threshold, role_threshold])
        else:
            id_list = await self.exec_sql(self.CHECK_SIMPLE, params=[role_threshold])
        return {x[0] for x in id_list}

    async def insert_rep(self, from_id: int, from_name: str, to_id: int, to_name: str, rep_dt: dt.datetime,
                         rep_msg: str = None, cooldown: int = None) -> bool:
        """
        :param from_id: UserID of the user that gives the rep.
        :param from_name: username#1234 of the user that gives the rep.
        :param to_id: UserID of the user that is being rep'd.
        :param to_name: username#1234 of the user that is being rep'd.
        :param rep_dt: The datetime that the reputation message was sent.
        :param rep_msg: (Optional) The message accompanied with the rep.
        :param cooldown: (Optional) The amount of seconds that need to have passed since the last time
               from_id rep'd to_id.
        :return: A boolean which determines whether a reputation was eligible to be inserted or not.
        """
        if cooldown:
            compare_stamp = rep_dt - dt.timedelta(seconds=cooldown)
            check_rows = await self.exec_sql(self.SELECT_REP_PAIR, [from_id, to_id, compare_stamp])
            can_insert = not check_rows  # Boolean, if check_rows is empty then the rep can be inserted.
        else:
            can_insert = True
        if can_insert:
            stamp = str(rep_dt)
            params = {"f_id": from_id, "f_n": from_name, "t_id": to_id, "t_n": to_name, "stamp": stamp, "msg": rep_msg}
            await self.exec_sql(self.INSERT_REP, params=params, commit=True)
        return can_insert

    async def user_rep_count(self, user_id: int) -> Tuple[int, int, Optional[str]]:
        """
        :param user_id: The userID of the user whose reputation count should be checked.
        :return: The tuple with the amount of reputations received, given by distinct count of users,
                 and the datetime string of the last reputation given.
        """
        resp = await self.exec_sql(self.SELECT_REP_COUNT, params=[user_id])
        assert resp, "No response from user_rep_count!"  # Should always return a response.
        return resp[0]

    async def rep_leaderboard(self) -> Optional[List[Tuple[int, int]]]:
        """
        :return: A list of tuples with the amount of reputations by userID, sorted on reputation count.

        Get the full leaderboard for reputations
        """
        leaderboard = await self.exec_sql(self.SELECT_LEADERBOARD)
        return leaderboard if leaderboard else None

    async def recent_reps(self, user_id: int, start_time: dt.datetime) -> int:
        """
        :param user_id: The userID of the user whose recent reps should be checked.
        :param start_time: The timestamp after which all reputations should be counted
        :return: An integer with the amount of reputations received by the user after start_time
        """
        resp = await self.exec_sql(self.GET_RECENT_REPS, params=[user_id, start_time])
        assert resp, "No response from recent_reps!"
        return resp[0][0]

    # Utilities.
    async def exec_sql(self, query, params=None, commit=False) -> list:
        """Make an asynchronous query to the reputation database"""
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(query, parameters=params) as cursor:
                rows = await cursor.fetchall()
            if commit:
                await db.commit()
        return rows
