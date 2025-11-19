from pyasic.device.algorithm import MinerAlgo
from pyasic.device.models import MinerModel
from pyasic.miners.device.makes import SealminerMake


class A2(SealminerMake):
    raw_model = MinerModel.SEALMINER.A2

    expected_chips = 153
    expected_hashboards = 3
    expected_fans = 4
    algo = MinerAlgo.SHA256
