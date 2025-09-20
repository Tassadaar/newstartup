import time

import numpy
import numpy as np
from brainflow import LogLevels, DataFilter, DetrendOperations, WindowOperations

from game.game import Game
from bci_control.brainflow_stream import BrainFlowBoard, compute_band_powers
from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams


def main():
    # board_id_cyton = BoardIds.CYTON_BOARD.value
    #
    # brainflow_board = BrainFlowBoard(board_id=board_id_cyton)
    #
    # brainflow_board.setup()
    #
    # # Stream from both boards for 5 seconds
    # time.sleep(5)
    #
    # # Retrieve and print data from the second board
    # data: numpy.ndarray = brainflow_board.get_board_data()
    #
    # BoardShim.enable_dev_board_logger()

    params = BrainFlowInputParams()

    board_id = BoardIds.SYNTHETIC_BOARD.value
    board_descr = BoardShim.get_board_descr(board_id)
    sampling_rate = int(board_descr['sampling_rate'])

    # for item1, item2 in board_descr:

    BoardShim.disable_board_logger()
    board = BoardShim(board_id, params)
    board.prepare_session()
    board.start_stream()


# use synthetic board for demo
    while True:
        BoardShim.log_message(LogLevels.LEVEL_INFO.value, 'start sleeping in the main thread')
        time.sleep(2)
        nfft = DataFilter.get_nearest_power_of_two(sampling_rate)
        data = board.get_current_board_data(num_samples=500)

        eeg_channels = board_descr['eeg_channels']
        # second eeg channel of synthetic board is a sine wave at 10Hz, should see huge alpha
        # NOTE: this is using c4
        eeg_data = data[1:4]


        def remove_dc_offset(data):
            return data[1:4, :] - np.mean(data[1:4, :], axis=1, keepdims=True)


        # optional detrend
        # DataFilter.detrend(data[eeg_channel], DetrendOperations.LINEAR.value)
        # psd = DataFilter.get_psd_welch(data[eeg_channel], nfft, nfft // 2, sampling_rate,
        #                                WindowOperations.BLACKMAN_HARRIS.value)
        eeg_data = remove_dc_offset(eeg_data)
        band_powers = compute_band_powers(eeg_data, sampling_rate, relative=True)
        print(band_powers)
        # print(f"alpha: {band_powers["alpha"]}")
        # print(f"beta: {band_powers["beta"]}")
        # print(f"a/b: {band_powers["alpha"] / band_powers["beta"]}")
        # print(f"b/a: {band_powers["beta"] / band_powers["alpha"]}")

    # board.stop_stream()
    # board.release_session()

# game = Game()
# game.run()

if __name__ == "__main__":
    main()
