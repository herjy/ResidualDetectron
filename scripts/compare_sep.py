import sep
import sys
import os
import numpy as np
BTK_PATH = '/home/users/sowmyak/BlendingToolKit/'
sys.path.insert(0, BTK_PATH)
import btk
CODE_PATH = '/home/users/sowmyak/ResidualDetectron/scripts'
sys.path.append(CODE_PATH)
import btk_utils
# Directory to save logs and trained model
MODEL_DIR = '/scratch/users/sowmyak/resid/logs'
# path to images
DATA_PATH = '/scratch/users/sowmyak/resid/data'


class Sep_params(btk.measure.Measurement_params):
    """Class containing functions to perform detection"""
    def get_centers(self, image):
        """Returns x and y coordinates of object centroids detected by sep.
        Detection is performed in the sum of all image bands.
        Args:
            image: multi-band image to perform detection on. ([#bands, x, y])
        Returns:
            x and y coordinates of detected centroids.
        """
        detect = image.mean(axis=0)  # simple average for detection
        bkg = sep.Background(detect)
        catalog = sep.extract(detect, 1.5, err=bkg.globalrms)
        return np.stack((catalog['x'], catalog['y']), axis=1)

    def get_deblended_images(self, data, index):
        """Returns detected centers for the given blend
        Args:
            data: output from btk.draw_blends generator
            index: index of blend in bacth_outputs to perform analysis on.
        Returns:
            deblended images and detected centers
        """
        image = np.transpose(data['blend_images'][index], axes=(2, 0, 1))
        peaks = self.get_centers(image)
        return [None, peaks]


class Sep_params_i_band(btk.measure.Measurement_params):
    """Class containing functions to perform detection"""
    def get_centers(self, image):
        """Returns x and y coordinates of object centroids detected by sep.
        Detection is performed in the i band.
        Args:
            image: multi-band image to perform detection on. ([#bands, x, y])
        Returns:
            x and y coordinates of detected centroids.
        """
        detect = image[3]  # detection in i band
        bkg = sep.Background(detect)
        catalog = sep.extract(detect, 1.5, err=bkg.globalrms)
        return np.stack((catalog['x'], catalog['y']), axis=1)

    def get_deblended_images(self, data, index):
        """Returns detected centers for the given blend
        Args:
            data: output from btk.draw_blends generator
            index: index of blend in bacth_outputs to perform analysis on.
        Returns:
            deblended images and detected centers
        """
        image = np.transpose(data['blend_images'][index], axes=(2, 0, 1))
        peaks = self.get_centers(image)
        return [None, peaks]


def get_btk_generator(meas_params, max_number, sampling_function,
                      selection_function, wld_catalog):
    """Returns btk.measure generator for input settings

    """
    # Input catalog name
    catalog_name = os.path.join("/scratch/users/sowmyak/data", 'OneDegSq.fits')
    # Load parameters
    param = btk.config.Simulation_params(
        catalog_name, max_number=max_number, batch_size=8, stamp_size=25.6)
    if wld_catalog:
            param.wld_catalog = wld_catalog
    np.random.seed(param.seed)
    # Load input catalog
    catalog = btk.get_input_catalog.load_catlog(
        param, selection_function=selection_function)
    # Generate catalogs of blended objects
    blend_generator = btk.create_blend_generator.generate(
        param, catalog, sampling_function)
    # Generates observing conditions for the selected survey_name & all bands
    observing_generator = btk.create_observing_generator.generate(
        param, btk_utils.resid_obs_conditions)
    # Generate images of blends in all the observing bands
    draw_blend_generator = btk.draw_blends.generate(
        param, blend_generator, observing_generator)
    meas_generator = btk.measure.generate(
        meas_params, draw_blend_generator, param)
    return meas_generator


def run_sep(save_file_name, test_size, meas_params, max_number,
            sampling_function, selection_function=None, wld_catalog=None):
    """Test performance for btk input blends"""
    meas_generator = get_btk_generator(
        max_number, sampling_function, selection_function, wld_catalog)
    results = []
    np.random.seed(1)
    for im_id in range(test_size):
        output, deb, _ = next(meas_generator)
        blend_list = output['blend_list'][0]
        detected_centers = deb[0][1]
        true_centers = np.stack([blend_list['dx'], blend_list['dy']]).T
        det, undet, spur = btk.compute_metrics.evaluate_detection(
            detected_centers, true_centers)
        print(len(true_centers), det, undet, spur)
        results.append([len(true_centers), det, undet, spur])
    arr_results = np.array(results).T
    print("Results: ", np.sum(arr_results, axis=1))
    np.savetxt(save_file_name, arr_results)


if __name__ == '__main__':
    max_number = 2
    test_size = 15
    # Run sep coadd detection
    meas_params = Sep_params
    save_file_name = f"sep_2gal_coadd_results.txt"
    run_sep(save_file_name, test_size, meas_params, max_number)
    # Run sep i band detection
    meas_params = Sep_params_i_band
    save_file_name = f"sep_2gal_iband_results.txt"
    run_sep(save_file_name, test_size, meas_params, max_number)
