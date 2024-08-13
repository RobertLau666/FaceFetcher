import os
import re
import time
import requests
from urllib import parse
from io import BytesIO

import cv2
import numpy as np
import PIL
from PIL import Image
import openpyxl
import xlrd
from xpinyin import Pinyin
from fake_useragent import UserAgent
from tqdm import tqdm


def create_dir_or_file(path):
    if not os.path.exists(path):
        file_name, file_extension = os.path.splitext(path)
        if file_extension == "":
            os.makedirs(path, exist_ok=True)
        else:
            if not os.path.exists(path):
                with open(path, 'w') as file:
                    pass

def read(img_save_path):
    img = cv2.imread(img_save_path)
    if img is None:
        return 0
    W, H = img.shape[1], img.shape[0]
    return img, W, H

def is_res_detect_ok(W, H):
    if W < resolution_boundary or H < resolution_boundary:
        print("0 res_detect | W, H: ", W, H)
        return False
    else:
        print("1 res_detect | W, H: ", W, H)
        return True

def is_face_area_ok(face_area, img_area):
    face_rate = face_area / img_area
    if face_rate < face_img_rate:
        print(f"0 face_area_ok | {face_area} / {img_area} = {face_rate} < {face_img_rate}")
        return False
    else:
        print(f"1 face_area_ok | {face_area} / {img_area} = {face_rate} >= {face_img_rate}")
        return True

def centered_square_crop(img, H, W, center):
    '''
    在给定图像的情况下，根据图像的尺寸和一个指定的中心点，将图像裁剪成一个正方形。裁剪后的正方形图像会尽可能保留以 center 为中心的区域。
    '''
    max_size = min(H, W)
    
    l_x, l_y = 0, 0

    if W > H:
        l_y = 0
        if center[0] < max_size // 2:
            l_x = 0
        elif center[0] > W - max_size // 2:
            l_x = W - max_size
        else:
            l_x = center[0] - max_size // 2
    elif H > W:
        l_x = 0
        if center[1] < max_size // 2:
            l_y = 0
        elif center[1] > H - max_size // 2:
            l_y = H - max_size
        else:
            l_y = center[1] - max_size // 2

    img = img[l_y:l_y + max_size, l_x:l_x + max_size]
    return img

def resize_image(img, resized_img_size_width, resized_img_size_height):
    '''
    对传入的图像进行重新缩放，将其调整为指定的宽度和高度。
    '''
    resized_img = cv2.resize(img, (int(resized_img_size_width), int(resized_img_size_height)))
    return resized_img

def read_excel(excel_path):
    book = xlrd.open_workbook(excel_path)
    sheet = book.sheet_by_name(sheet_name)
    nrows, ncols = sheet.nrows, sheet.ncols

    name_list = []
    for i in range(nrows):
        row = sheet.row_values(i)
        name_list.append(row)

    return name_list

def number_to_letter(num):
    letter = chr(64 + num)
    return letter

def cn2en_write(excel_path):
    book = xlrd.open_workbook(excel_path)
    sheet = book.sheet_by_name(sheet_name)
    cn_names = sheet.col_values(0)
    cn_names = list(set([cn_name for cn_name in cn_names if cn_name != ""]))
    print("cn_names", cn_names, len(cn_names))

    p = Pinyin()
    cn_en_name_list = []
    for i in range(len(cn_names)):
        result1 = p.get_pinyin(cn_names[i])
        s = result1.split('-')
        result3 = s[0].capitalize() + ''.join(s[1:]).capitalize()
        cn_en_name_list.append([cn_names[i], result3, 0])
    cn_en_name_list = sorted(cn_en_name_list, key=lambda x: x[1])
    print('cn_en_name_list', cn_en_name_list)
    
    wb = openpyxl.load_workbook(excel_path)
    ws = wb[sheet_name]

    # Set to blank firstly
    for row in ws.iter_rows():
        for cell in row:
            cell.value = None
    
    for r in range(len(cn_en_name_list)):
        for c in range(len(cn_en_name_list[0])):
            ws[f"{number_to_letter(c + 1)}" + str(r + 1)] = cn_en_name_list[r][c]
    wb.save(excel_path)

    return cn_en_name_list

class Spider:
    def __init__(self, index, cn_name, en_name, en_name_dir):
        self.index = index
        self.cn_name = cn_name
        self.en_name = en_name
        self.en_name_dir = en_name_dir
        self.name = parse.quote(self.cn_name + limit)
        self.times = str(int(time.time() * 1000))

        self.url = None
        if size_type == "all": # 全部尺寸
            self.url = 'https://image.baidu.com/search/acjson?tn=resultjson_com&logid=8032920601831512061&ipn=rj&ct=201326592&is=&fp=result&fr=&word={}&cg=star&queryWord={}&cl=2&lm=-1&ie=utf-8&oe=utf-8&adpicid=&st=&z=&ic=&hd=&latest=&copyright=&s=&se=&tab=&width=&height=&face=&istype=&qc=&nc=1&expermode=&nojc=&isAsync=&pn={}&rn=30&gsm=1e&{}='
        elif size_type == "extra large": # 特大尺寸
            self.url = 'https://image.baidu.com/search/acjson?tn=resultjson_com&logid=5314417940526052016&ipn=rj&ct=201326592&is=&fp=result&fr=&word={}&cg=star&queryWord={}&cl=2&lm=-1&ie=utf-8&oe=utf-8&adpicid=&st=&z=9&ic=&hd=&latest=&copyright=&s=&se=&tab=&width=0&height=0&face=&istype=&qc=&nc=&expermode=&nojc=&isAsync=&pn={}&rn=30&gsm=1e&{}='
        else: # 未指定尺寸，则默认用全部尺寸
            self.url = 'https://image.baidu.com/search/acjson?tn=resultjson_com&logid=8032920601831512061&ipn=rj&ct=201326592&is=&fp=result&fr=&word={}&cg=star&queryWord={}&cl=2&lm=-1&ie=utf-8&oe=utf-8&adpicid=&st=&z=&ic=&hd=&latest=&copyright=&s=&se=&tab=&width=&height=&face=&istype=&qc=&nc=1&expermode=&nojc=&isAsync=&pn={}&rn=30&gsm=1e&{}='
        
        self.headers = {'User-Agent': UserAgent().random}

    # 请求30张图片的链接
    def get_one_html(self, url, pn):
        while True:
            try:
                response = requests.get(url=url.format(self.name, self.name, pn, self.times), headers=self.headers).content.decode('utf-8')
                break
            except Exception as e:
                print(f"error {e} occurred. Retrying...")
                time.sleep(1)
        return response

    # 请求单张图片内容
    def get_two_html(self, url):
        while True:
            try:
                response = requests.get(url=url, headers=self.headers).content
                break
            except Exception as e:
                print(f"error {e} occurred. Retrying...")
                time.sleep(1)
        return response

    # 解析含30张图片的html的内容
    def parse_html(self, regex, html):
        content = regex.findall(html)
        return content

    def well_detection(self, img, img_save_path):
        W, H = img.shape[1], img.shape[0]
        print('W, H读取没问题')

        res_detect_ok = is_res_detect_ok(W, H)
        if not res_detect_ok:
            return 0

        # 检测人脸
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        if len(faces) >= 1:
            print("1 faces | len(faces): ", len(faces))
            for (x, y, w, h) in faces:
                print('Dealing with circular face: ', img_save_path)
                # 不需要画上框格
                # img=cv2.rectangle(img,(x,y),(x+w,y+h),(255,0,0),2)

                # Define the region of interest in the image  
                # img = img[y:y+h, x:x+w]

                # l_x,l_y=x-int((w//2)*(b-1)),y-int((h//2)*(b-1))
                # r_x,r_y=x+w+int((w//2)*(b-1)),y+h+int((h//2)*(b-1))
                # if l_x<0:l_x=0
                # if l_y<0:l_y=0
                # if r_x>H:r_x=H
                # if r_y>W:r_y>W
                
                # 判断人脸大小是否满足比例
                face_area, img_area = w*h, H*W
                face_area_ok = is_face_area_ok(face_area, img_area)
                if not face_area_ok:
                    return 0
                else:
                    if centered_square_crop_mode:
                        center = [(2 * x + w) // 2, (2 * y + h) // 2]
                        img = centered_square_crop(img, H, W, center)
                    if resize_mode:
                        img = resize_image(img, resized_img_size_width, resized_img_size_height)
                    cv2.imwrite(img_save_path, img)
                    return 1
        else:
            print("0 faces | len(faces): ", len(faces))
            return 0

    def run(self):
        response = self.get_one_html(self.url, 0)
        regex1 = re.compile('"displayNum":(.*?),')
        num = self.parse_html(regex1, response)[0] # 获取总的照片数量
        print('{}{}一共有{}张照片'.format(self.cn_name, self.en_name, num)) # 打印总的照片数量

        # 判断总数能不能整除30
        if int(num) % 30 == 0:
            pn = int(num) / 30
        else:
            # 总数量除30是因为每一个链接有30张照片 +2是因为要想range最多取到该数就需要+1
            # 另外的+1是因为该总数除30可能有余数，有余数就需要一个链接 所以要+1
            pn = int(num) // 30 + 2

        img_record_num = len(os.listdir(os.path.join(save_root_dir, sheet_name, self.en_name)))
        for i in range(int(pn)): # 遍历每一个含30张图片的链接
            resp = self.get_one_html(self.url, i * 30)
            urls = re.findall('"ObjURL":"(.*?)",', resp, re.S)
            for i in range(len(urls)):
                urls[i] = ''.join(urls[i].split('\\'))
            print("urls: ", urls)

            for j, url in enumerate(urls):  # 遍历每张图片的链接
                print('url: ', url)
                if url.split(':')[0] == 'https':
                    try:
                        response = requests.get(url=url, headers=self.headers, timeout=(20.00, 10.00))
                        content = response.content
                    except requests.exceptions.ConnectionError as e:
                        print('ConnectionError:', e)
                        continue
                    except requests.exceptions.ReadTimeout as e:
                        print('ReadTimeout:', e)
                        continue
                    except requests.exceptions.ChunkedEncodingError as e:
                        print('ChunkedEncodingError:', e)
                        continue

                    try:
                        img = Image.open(BytesIO(content)).convert("RGB")
                    except PIL.UnidentifiedImageError as e:
                        print('PIL.UnidentifiedImageError:', e)
                        continue
                    except OSError as e:
                        print('OSError:', e)
                        continue
                    img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)

                    img_save_path = os.path.join(save_root_dir, sheet_name, self.en_name_dir, f'{img_record_num}.jpg')

                    # 看是否满足条件
                    res = self.well_detection(img, img_save_path)

                    if res == 1:
                        img_record_num += 1
                        print('saved 第{}人{}{}, 第{}/{}张照片, img_save_path:{}\n'.format(self.index, self.cn_name, self.en_name, img_record_num, fetch_image_nums_per_person, img_save_path))
                    else:
                        print('不满足条件\n')

                if img_record_num == fetch_image_nums_per_person:
                    break
            if img_record_num == fetch_image_nums_per_person:
                break



## 基本参数设置
excel_path = 'person_names.xlsx'
sheet_name = 'Sheet_man'
save_root_dir = 'output'
# 每个人需要下载多少张图片
fetch_image_nums_per_person = 10
# 从第几个人开始 第一行的序号为0
start_fetch_row = 0

## 筛选
# 指定下载图片尺寸类型
size_type = "extra large"
# 放大倍数
# enlarge_factor = 1.5
# 裁剪后可接受的长宽比
# acceptable_aspect_ratio = 1.3
# '正脸 高清 大尺寸'
limit = ''
# 分别对应 全部尺寸0 特大尺寸9 大尺寸3 中尺寸2 小尺寸1 暂时没用到该参数 还是调上面self.url就行了
size_level = 9
# 分辨率分界线，长或宽低于这个的pass掉
resolution_boundary = 768
# 脸图比例，小于这个不考虑
face_img_rate = 0.03

## 后处理
centered_square_crop_mode = True
resize_mode = True
# resize后的图像大小
resized_img_size_width = 768
resized_img_size_height = 768


def main():
    create_dir_or_file(save_root_dir)
    # 中文名转为英文名，写入文件
    cn2en_write(excel_path)

    # 获取中英名list:[[cn,en],[cn,en],...]
    name_list = read_excel(excel_path)
    print('name_list: ', name_list)

    for index in tqdm(range(start_fetch_row, len(name_list))):
        cn_name, en_name = name_list[index][0], name_list[index][1]
        en_name_dir = os.path.join(save_root_dir, sheet_name, en_name)
        if os.path.exists(en_name_dir) and len(os.listdir(en_name_dir)) == fetch_image_nums_per_person:
            continue
        else:
            create_dir_or_file(en_name_dir)
            print('Downloading images: {}/{}: {} {}'.format(index, len(name_list), cn_name, en_name))
            spider = Spider(index, cn_name, en_name, en_name)
            spider.run()

if __name__ == '__main__':
    main()
