# FaceFetcher
## Install
```
git clone https://github.com/RobertLau666/FaceFetcher.git
cd FaceFetcher
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```
## Prepare
1. Put the person names you want to fetch in the first column of any Sheet in ```person_names.xlsx```.
2. Modify parameters in ```app.py```.
> Don't worry about duplicate names in the same column, the program will automatically merge the duplicate names.
## Run
```
python app.py
```
## Download
You can download the fetched images of ```person_names.xlsx``` from [here](https://drive.google.com/drive/folders/1JiR2HGW2DwlLVyxhAfPeI15_o-97nBC5?usp=sharing).
## Result presentation
![demo.jpeg](assets/demo_images/demo.webp)