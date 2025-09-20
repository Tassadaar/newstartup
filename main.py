import time

import numpy
import numpy as np
from brainflow import LogLevels, DataFilter, DetrendOperations, WindowOperations

from game.game import Game
from bci_control.brainflow_stream import BrainFlowBoard, compute_band_powers
from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams


def main():
    params = BrainFlowInputParams()

    board_id = BoardIds.CYTON_BOARD.value
    board = BrainFlowBoard(board_id = board_id, serial_port="/dev/cu.usbserial-DM01IK21")
    board.setup()
    board_descr = BoardShim.get_board_descr(board_id)
    sampling_rate = int(board_descr['sampling_rate'])

    while True:
        BoardShim.log_message(LogLevels.LEVEL_INFO.value, 'start sleeping in the main thread')
        time.sleep(2)
        nfft = DataFilter.get_nearest_power_of_two(sampling_rate)
        data = board.get_current_board_data(num_samples=500)

        eeg_channels = board_descr['eeg_channels']
        # NOTE: this is using c4
        eeg_data = data


        def remove_dc_offset(data):
            return data[1:4, :] - np.mean(data[1:4, :], axis=1, keepdims=True)
        eeg_data = remove_dc_offset(eeg_data)
        band_powers = compute_band_powers(eeg_data, sampling_rate, relative=True)
        powers, _ = band_powers


    # board.stop_stream()
    # board.release_session()



if __name__ == "__main__":
    main()
