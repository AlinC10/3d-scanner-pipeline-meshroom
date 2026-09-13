# `ram_heuristic.py`

## API Reference

### `def calculate_required_ram(num_images, resolution_mp=12.0, depthmap_downscale=2, max_input_points=10000000, two_sides_mode=False)`
> Empirical equation for calculating Meshroom RAM requirements.
> RAM_GB = O + (N * R * K) + (P / 1.5e6)
> 
> :param num_images: Number of input photos
> :type num_images: int
> :param resolution_mp: Resolution of the photos in megapixels
> :type resolution_mp: float
> :param depthmap_downscale: Downscale factor for the DepthMap node (typically 1 or 2)
> :type depthmap_downscale: int
> :param max_input_points: The maxInputPoints parameter for the Meshing node
> :type max_input_points: int
> :param two_sides_mode: Whether the pipeline is running in two-sides mode (doubles image load)
> :type two_sides_mode: bool
> :return: The calculated safe minimum RAM requirement in GB (including a 10% safety buffer)
> :rtype: int
