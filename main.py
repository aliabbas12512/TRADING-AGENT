import logging

from trading_agent.agent import TradingAgent
from trading_agent.config import Config


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    config = Config.from_env()
    agent = TradingAgent(config)
    agent.run_forever()


if __name__ == "__main__":
    main()
