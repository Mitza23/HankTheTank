The following repository represents an alteration of the official YOLOv7 repository
My contribution comes in the form of my personal dataset preparation present in dataset_preparation.py
or data_preparation.ipynb
Another modification I did was in test_images.py where I modified detect.py from the official repo in order to better
suit my needs for output: getting the coordinates of bounding boxes. There are helper functions which in turn
aid with the better visualization of the detection
The weights have also been uploaded due to the fact that I also need them on other devices

The user needs to have CUDA installed and pytorch downloaded with support for the respective version of CUDA
<br />
Python 3.7.7 is recommended
<br />
Use `pip install -r requirements.txt` to install the necessary packages and run the app from pycharm
<br />
or for the command line, open the terminal in this directory and use:
<br />
`pip install .`
<br />
followed by
<br />
`venv\Scripts\activate`
<br />
and
<br />
`hank`
<br />

For best performance:<br />
Keep CS:GO on settings as low as possible, especially resolution.<br />
Close as many background processes as possible.<br />
<br />
<br />
Hank has been trained on Dust 2, so there you'll get the best results.<br />