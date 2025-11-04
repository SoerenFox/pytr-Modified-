#!/usr/bin/env python

import argparse
import asyncio
import json
import shutil
import signal
from datetime import datetime, timedelta
from importlib.metadata import version
from pathlib import Path

import shtab

from pytr.account import login
from pytr.alarms import Alarms
from pytr.details import Details
from pytr.dl import DL
from pytr.event import Event
from pytr.portfolio import Portfolio
from pytr.stoploss import StopLossUpdater
from pytr.orderOverview import OrderOverview
from pytr.news import News
from pytr.transactions import SUPPORTED_LANGUAGES, TransactionExporter
from pytr.utils import check_version, get_logger


def get_main_parser():
    def formatter(prog):
        width = min(shutil.get_terminal_size().columns // 3, 80)
        return argparse.ArgumentDefaultsHelpFormatter(prog, max_help_position=width)

    parser = argparse.ArgumentParser(
        formatter_class=formatter,
        description='Use "%(prog)s command_name --help" to get detailed help to a specific command',
    )
    for grp in parser._action_groups:
        if grp.title == "options":
            grp.title = "Options"
        elif grp.title == "positional arguments":
            grp.title = "Commands"

    parser.add_argument(
        "-V",
        "--version",
        help="Print version information and quit",
        action="store_true",
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        help="Set verbosity level (default: info)",
        choices=["warning", "info", "debug"],
        default="info",
    )
    parser.add_argument(
        "--debug-logfile",
        help="Dump debug logs to a file",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--debug-log-filter",
        help="Filter debug log types",
        default=None,
    )

    parser_cmd = parser.add_subparsers(help="Desired action to perform", dest="command")

    # help
    parser_cmd.add_parser(
        "help",
        help="Print this help message",
        description="Print help message",
        add_help=False,
    )

    # parent subparser with common login arguments
    parser_login_args = argparse.ArgumentParser(add_help=False)
    parser_login_args.add_argument("--applogin", help="Use app login instead of  web login", action="store_true")
    parser_login_args.add_argument("-n", "--phone_no", help="TradeRepublic phone number (international format)")
    parser_login_args.add_argument("-p", "--pin", help="TradeRepublic pin")
    parser_login_args.add_argument(
        "--store_credentials",
        help="Store credentials (Phone number, pin, cookies) for next usage",
        action="store_true",
        default=True,
    )

    # parent subparser for lang option
    parser_lang = argparse.ArgumentParser(add_help=False)
    parser_lang.add_argument(
        "-l",
        "--lang",
        help='Two letter language code or "auto" for system language.',
        choices=["auto", *sorted(SUPPORTED_LANGUAGES)],
        default="auto",
    )

    # parent subparser for date-with-time option
    parser_date_with_time = argparse.ArgumentParser(add_help=False)
    parser_date_with_time.add_argument(
        "--date-with-time",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Whether to include the timestamp in the date column.",
    )

    # parent subparser for decimal-localization option
    parser_decimal_localization = argparse.ArgumentParser(add_help=False)
    parser_decimal_localization.add_argument(
        "--decimal-localization",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Whether to localize decimal numbers.",
    )

    # parent subparser for sorting option
    parser_sort_export = argparse.ArgumentParser(add_help=False)
    parser_sort_export.add_argument(
        "-s",
        "--sort",
        help="Chronologically sort exported csv transactions",
        action="store_true",
    )

    # login
    info = (
        "Check if credentials file exists. If not create it and ask for input. Try to login."
        + " Ask for device reset if needed"
    )
    parser_cmd.add_parser(
        "login",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )

    # dl_docs
    info = (
        "Download all pdf documents from the timeline and sort them into folders."
        + " Also export account transactions (account_transactions.csv)"
        + " and JSON files with all events (events_with_documents.json and other_events.json)"
    )
    parser_dl_docs = parser_cmd.add_parser(
        "dl_docs",
        formatter_class=formatter,
        parents=[
            parser_login_args,
            parser_lang,
            parser_date_with_time,
            parser_decimal_localization,
            parser_sort_export,
        ],
        help=info,
        description=info,
    )

    parser_dl_docs.add_argument("output", help="Output directory", metavar="PATH", type=Path)
    parser_dl_docs.add_argument(
        "--format",
        help="available variables:\tiso_date, time, title, subtitle, doc_num, id",
        metavar="FORMAT_STRING",
        default="{iso_date} {time} {title}",
    )
    parser_dl_docs.add_argument(
        "--last_days",
        help="Number of last days to include (use 0 get all days)",
        metavar="DAYS",
        default=0,
        type=int,
    )
    parser_dl_docs.add_argument(
        "--workers",
        help="Number of workers for parallel downloading",
        default=8,
        type=int,
    )
    parser_dl_docs.add_argument("--universal", help="Platform independent file names", action="store_true")
    parser_dl_docs.add_argument(
        "--export-format",
        choices=("json", "csv"),
        default="csv",
        help="The output file format.",
    )

    # portfolio
    info = "Show current portfolio"
    parser_portfolio = parser_cmd.add_parser(
        "portfolio",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )
    parser_portfolio.add_argument("-o", "--output", help="Output path of CSV file", type=Path)

    # details
    info = "Get details for an ISIN"
    parser_details = parser_cmd.add_parser(
        "details",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )
    parser_details.add_argument("isin", help="ISIN of intrument")

    # savings_plans
    info = "Show savings plans overview"
    parser_savings = parser_cmd.add_parser(
        "savings_plans",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )
    # small read-only helpers
    info = "Show compact portfolio"
    parser_compact_portfolio = parser_cmd.add_parser(
        "compact_portfolio",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )

    info = "Show portfolio status"
    parser_portfolio_status = parser_cmd.add_parser(
        "portfolio_status",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )

    info = "Show watchlist"
    parser_watchlist = parser_cmd.add_parser(
        "watchlist",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )

    info = "Show cash positions"
    parser_cash = parser_cmd.add_parser(
        "cash",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )

    info = "Get ticker for an ISIN"
    parser_ticker = parser_cmd.add_parser(
        "ticker",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )
    parser_ticker.add_argument("isin", help="ISIN of instrument")
    parser_ticker.add_argument("--exchange", default="LSX", help="Exchange id (default: LSX)")

    info = "Get performance for an ISIN"
    parser_performance = parser_cmd.add_parser(
        "performance",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )
    parser_performance.add_argument("isin", help="ISIN of instrument")
    parser_performance.add_argument("--exchange", default="LSX", help="Exchange id (default: LSX)")

    info = "Show timeline (optional: after id)"
    parser_timeline = parser_cmd.add_parser(
        "timeline",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )
    parser_timeline.add_argument("--after", help="Fetch timeline after this id", default=None)

    info = "Show timeline detail"
    parser_timeline_detail = parser_cmd.add_parser(
        "timeline_detail",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )
    parser_timeline_detail.add_argument("id", help="Timeline detail id")

    info = "Search suggested tags"
    parser_search_suggested = parser_cmd.add_parser(
        "search_suggested_tags",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )
    parser_search_suggested.add_argument("query", help="Query string")

    info = "Search instruments"
    parser_search = parser_cmd.add_parser(
        "search",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )
    parser_search.add_argument("query", help="Query string")
    parser_search.add_argument("--asset_type", default="stock", help="Asset type (default: stock)")

    info = "Show order overview"
    parser_order_overview = parser_cmd.add_parser(
        "order_overview",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )

    info = "Price for order"
    parser_price_for_order = parser_cmd.add_parser(
        "price_for_order",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )
    parser_price_for_order.add_argument("isin", help="ISIN of instrument")
    parser_price_for_order.add_argument("exchange", help="Exchange id")
    parser_price_for_order.add_argument("order_type", help="Order type (buy/sell)")

    # automated stop order
    info = "Update all stop-loss orders to by default 5 percent below current market price"
    parser_stoploss_update = parser_cmd.add_parser(
        "update_stoploss",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )
    parser_stoploss_update.add_argument(
        "--percent",
        help="Percentage below market price for stop loss",
        type=float,
        default=5.0,
    )
    parser_stoploss_update.add_argument(
        "--expiry",
        help="Expiry type (gfd/gtd)",
        default="gfd",
    )
    parser_stoploss_update.add_argument(
        "--expiry-date",
        help="Expiry date for gtd (YYYY-MM-DD)",
        default=None,
    )


    # Limit order
    parser_limit_order = parser_cmd.add_parser(
        "limit_order",
        formatter_class=formatter,
        parents=[parser_login_args],
        help="Place a limit order",
        description="Place a limit order",
    )
    parser_limit_order.add_argument("isin", help="ISIN of instrument")
    parser_limit_order.add_argument("exchange", help="Exchange id")
    parser_limit_order.add_argument("order_type", help="Order type (buy/sell)")
    parser_limit_order.add_argument("size", help="Order size", type=float)
    parser_limit_order.add_argument("limit", help="Limit price", type=float)
    parser_limit_order.add_argument(
        "--expiry",
        help="Expiry type (gfd/gtd)",
        default="gfd",
    )
    parser_limit_order.add_argument(
        "--expiry-date",
        help="Expiry date for gtd (YYYY-MM-DD)",
        default=None,
    )
    parser_limit_order.add_argument(
        "--warnings-shown",
        help="Optional comma separated list of warningsShown",
        default=None,
    )

    info = "Show news for an ISIN"
    parser_news = parser_cmd.add_parser(
        "news",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )
    parser_news.add_argument("isin", help="ISIN of instrument")

    # Portfolio news
    info = "Show news for all portfolio instruments"
    parser_news = parser_cmd.add_parser(
        "portfolio_news",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )

    # Cancel order
    parser_cancel_order = parser_cmd.add_parser(
        "cancel_order",
        formatter_class=formatter,
        parents=[parser_login_args],
        help="Cancel an order",
        description="Cancel an existing order by id",
    )
    parser_cancel_order.add_argument("order_id", help="Order id to cancel")
    
    # get_price_alarms
    info = "Get current price alarms"
    parser_get_price_alarms = parser_cmd.add_parser(
        "get_price_alarms",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )
    parser_get_price_alarms.add_argument(
        "input", nargs="*", help="Input data in the form of <ISIN1> <ISIN2> ...", default=[]
    )
    parser_get_price_alarms.add_argument(
        "--outputfile",
        help="Output file path",
        type=argparse.FileType("w", encoding="utf-8"),
        default="-",
        nargs="?",
    )

    # set_price_alarms
    info = "Set new price alarms"
    parser_set_price_alarms = parser_cmd.add_parser(
        "set_price_alarms",
        formatter_class=formatter,
        parents=[parser_login_args],
        help=info,
        description=info,
    )
    parser_set_price_alarms.add_argument(
        "input", nargs="*", help="Input data in the form of <ISIN> <alarm1> <alarm2> ...", default=[]
    )
    parser_set_price_alarms.add_argument(
        "--remove-current-alarms",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Whether to remove current alarms.",
    )
    parser_set_price_alarms.add_argument(
        "--inputfile",
        help="Input file path",
        type=argparse.FileType("r", encoding="utf-8"),
        default="-",
        nargs="?",
    )

    # export_transactions
    info = "Create a CSV with the deposits and removals ready for importing into Portfolio Performance"
    parser_export_transactions = parser_cmd.add_parser(
        "export_transactions",
        formatter_class=formatter,
        parents=[parser_lang, parser_date_with_time, parser_decimal_localization, parser_sort_export],
        help=info,
        description=info,
    )
    parser_export_transactions.add_argument(
        "input",
        help="Input path to JSON (use all_events.json from dl_docs)",
        type=argparse.FileType("r", encoding="utf-8"),
    )
    parser_export_transactions.add_argument(
        "output",
        help="Output file path",
        type=argparse.FileType("w", encoding="utf-8"),
        default="-",
        nargs="?",
    )
    parser_export_transactions.add_argument(
        "--format",
        choices=("json", "csv"),
        default="csv",
        help="The output file format.",
    )

    info = "Print shell tab completion"
    parser_completion = parser_cmd.add_parser(
        "completion",
        formatter_class=formatter,
        help=info,
        description=info,
    )
    shtab.add_argument_to(parser_completion, "shell", parent=parser)
    return parser


def exit_gracefully(signum, frame):
    # restore the original signal handler as otherwise evil things will happen
    # in input when CTRL+C is pressed, and our signal handler is not re-entrant
    global original_sigint
    signal.signal(signal.SIGINT, original_sigint)

    try:
        if input("\nReally quit? (y/n)> ").lower().startswith("y"):
            exit(1)

    except KeyboardInterrupt:
        print("Ok ok, quitting")
        exit(1)

    # restore the exit gracefully handler here
    signal.signal(signal.SIGINT, exit_gracefully)


def main():
    # store the original SIGINT handler
    global original_sigint
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, exit_gracefully)

    parser = get_main_parser()
    args = parser.parse_args()
    # print(vars(args))

    log = get_logger(__name__, args.verbosity, args.debug_logfile, args.debug_log_filter)
    if args.verbosity.upper() == "DEBUG":
        log.debug("logging is set to debug")

    if args.command == "login":
        login(
            phone_no=args.phone_no,
            pin=args.pin,
            web=not args.applogin,
            store_credentials=args.store_credentials,
        )

    elif args.command == "dl_docs":
        if args.last_days == 0:
            since_timestamp = 0
        else:
            since_timestamp = (datetime.now().astimezone() - timedelta(days=args.last_days)).timestamp()
        dl = DL(
            login(
                phone_no=args.phone_no,
                pin=args.pin,
                web=not args.applogin,
                store_credentials=args.store_credentials,
            ),
            args.output,
            args.format,
            since_timestamp=since_timestamp,
            max_workers=args.workers,
            universal_filepath=args.universal,
            lang=args.lang,
            date_with_time=args.date_with_time,
            decimal_localization=args.decimal_localization,
            sort_export=args.sort,
            format_export=args.export_format,
        )
        asyncio.get_event_loop().run_until_complete(dl.dl_loop())
    elif args.command == "get_price_alarms":
        try:
            Alarms(
                login(
                    phone_no=args.phone_no,
                    pin=args.pin,
                    web=not args.applogin,
                    store_credentials=args.store_credentials,
                ),
                args.input,
                args.outputfile,
            ).get()
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "compact_portfolio":
        try:
            tr = login(phone_no=args.phone_no, pin=args.pin, web=not args.applogin, store_credentials=args.store_credentials)
            res = tr.blocking_compact_portfolio()
            print(json.dumps(res, indent=2, ensure_ascii=False))
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "portfolio_status":
        try:
            tr = login(phone_no=args.phone_no, pin=args.pin, web=not args.applogin, store_credentials=args.store_credentials)
            res = tr.blocking_portfolio_status()
            print(json.dumps(res, indent=2, ensure_ascii=False))
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "watchlist":
        try:
            tr = login(phone_no=args.phone_no, pin=args.pin, web=not args.applogin, store_credentials=args.store_credentials)
            res = tr.blocking_watchlist()
            print(json.dumps(res, indent=2, ensure_ascii=False))
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "cash":
        try:
            tr = login(phone_no=args.phone_no, pin=args.pin, web=not args.applogin, store_credentials=args.store_credentials)
            res = tr.blocking_cash()
            print(json.dumps(res, indent=2, ensure_ascii=False))
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "ticker":
        try:
            tr = login(phone_no=args.phone_no, pin=args.pin, web=not args.applogin, store_credentials=args.store_credentials)
            res = tr.blocking_ticker(args.isin, exchange=args.exchange)
            print(json.dumps(res, indent=2, ensure_ascii=False))
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "performance":
        try:
            tr = login(phone_no=args.phone_no, pin=args.pin, web=not args.applogin, store_credentials=args.store_credentials)
            res = tr.blocking_performance(args.isin, exchange=args.exchange)
            print(json.dumps(res, indent=2, ensure_ascii=False))
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "timeline":
        try:
            tr = login(phone_no=args.phone_no, pin=args.pin, web=not args.applogin, store_credentials=args.store_credentials)
            if args.after:
                res = tr.blocking_timeline(after=args.after)
            else:
                res = tr.blocking_timeline()
            print(json.dumps(res, indent=2, ensure_ascii=False))
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "timeline_detail":
        try:
            tr = login(phone_no=args.phone_no, pin=args.pin, web=not args.applogin, store_credentials=args.store_credentials)
            res = tr.blocking_timeline_detail(args.id)
            print(json.dumps(res, indent=2, ensure_ascii=False))
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "search_suggested_tags":
        try:
            tr = login(phone_no=args.phone_no, pin=args.pin, web=not args.applogin, store_credentials=args.store_credentials)
            res = tr.blocking_search_suggested_tags(args.query)
            print(json.dumps(res, indent=2, ensure_ascii=False))
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "search":
        try:
            tr = login(phone_no=args.phone_no, pin=args.pin, web=not args.applogin, store_credentials=args.store_credentials)
            res = tr.blocking_search(args.query, asset_type=args.asset_type)
            print(json.dumps(res, indent=2, ensure_ascii=False))
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "order_overview":
        try:
            OrderOverview(
                login(
                    phone_no=args.phone_no,
                    pin=args.pin,
                    web=not args.applogin,
                    store_credentials=args.store_credentials,
                )
            ).get()
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "price_for_order":
        try:
            tr = login(phone_no=args.phone_no, pin=args.pin, web=not args.applogin, store_credentials=args.store_credentials)
            res = tr.blocking_price_for_order(args.isin, args.exchange, args.order_type)
            print(json.dumps(res, indent=2, ensure_ascii=False))
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "update_stoploss":
        try:
            StopLossUpdater(
                login(
                    phone_no=args.phone_no,
                    pin=args.pin,
                    web=not args.applogin,
                    store_credentials=args.store_credentials,
                )
            ).update(percent_diff=args.percent / 100, expiry=args.expiry, expiry_date=args.expiry_date)
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "limit_order":
        try:
            tr = login(phone_no=args.phone_no, pin=args.pin, web=not args.applogin, store_credentials=args.store_credentials)
            warnings = args.warnings_shown.split(",") if args.warnings_shown else None
            res = tr.blocking_limit_order(
                args.isin,
                args.exchange,
                args.order_type,
                args.size,
                args.limit,
                args.expiry,
                expiry_date=args.expiry_date,
                warnings_shown=warnings,
            )
            print(json.dumps(res, indent=2, ensure_ascii=False))
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "cancel_order":
        try:
            tr = login(phone_no=args.phone_no, pin=args.pin, web=not args.applogin, store_credentials=args.store_credentials)
            res = tr.blocking_cancel_order(args.order_id)
            print(json.dumps(res, indent=2, ensure_ascii=False))
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "news":
        try:
            News(
                login(
                    phone_no=args.phone_no,
                    pin=args.pin,
                    web=not args.applogin,
                    store_credentials=args.store_credentials,
                )
            ).get(args.isin)
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "portfolio_news":
        try:
            News(
                login(
                    phone_no=args.phone_no,
                    pin=args.pin,
                    web=not args.applogin,
                    store_credentials=args.store_credentials,
                )
            ).getForPortfolio()
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "set_price_alarms":
        try:
            Alarms(
                login(
                    phone_no=args.phone_no,
                    pin=args.pin,
                    web=not args.applogin,
                    store_credentials=args.store_credentials,
                ),
                args.input,
                args.inputfile,
                args.remove_current_alarms,
            ).set()
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "details":
        Details(
            login(
                phone_no=args.phone_no,
                pin=args.pin,
                web=not args.applogin,
                store_credentials=args.store_credentials,
            ),
            args.isin,
        ).get()
    elif args.command == "savings_plans":
        try:
            tr = login(
                phone_no=args.phone_no,
                pin=args.pin,
                web=not args.applogin,
                store_credentials=args.store_credentials,
            )
            # use the blocking helper generated by __getattr__ (blocking_savings_plan_overview)
            plans = tr.blocking_savings_plan_overview()
            print(json.dumps(plans, indent=2, ensure_ascii=False))
        except ValueError as e:
            print(e)
            return -1
    elif args.command == "portfolio":
        p = Portfolio(
            login(
                phone_no=args.phone_no,
                pin=args.pin,
                web=not args.applogin,
                store_credentials=args.store_credentials,
            )
        )
        p.get()
        if args.output is not None:
            p.portfolio_to_csv(args.output)
    elif args.command == "export_transactions":
        events = [Event.from_dict(item) for item in json.load(args.input)]
        TransactionExporter(
            lang=args.lang,
            date_with_time=args.date_with_time,
            decimal_localization=args.decimal_localization,
        ).export(
            fp=args.output,
            events=events,
            sort=args.sort,
            format=args.format,
        )
    elif args.version:
        installed_version = version("pytr")
        print(installed_version)
        check_version(installed_version)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
