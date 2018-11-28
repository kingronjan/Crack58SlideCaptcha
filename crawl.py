import cv2
import numpy as np
import time
import random
from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.webdriver import ActionChains

# 截屏后图片保存路径
captcha_img = 'captcha_image.png'

# 方块和缺口所在区域、图片路径
left_region = (0, 0, 63, 169)
right_region = (63, 0, 300, 169)
left_image = 'left.png'
right_image = 'right.png'

class CrackSlideCaptcha(object):

    def __init__(self, url):
        self.br = webdriver.Firefox(executable_path=
                                    r'D:\Program Files\drivers\geckodriver.exe')
        self.url = url

    def get_image(self):
        ' 找到图片位置，全屏截图，剪裁并存储. '
        self.br.get(self.url)
        time.sleep(1)
        button = self.br.find_element_by_id('btnSubmit')
        button.click()
        time.sleep(1)
        image = self.br.find_element_by_xpath('//div[@class="dvc-placeholder"]')
        location = image.location
        size = image.size
        top, bottom, left, right = location['y'], location['y']+size['height'], \
                                   location['x'], location['x']+size['width']
        screenshot = self.br.get_screenshot_as_png()
        screenshot = Image.open(BytesIO(screenshot))
        captcha = screenshot.crop((left, top, right, bottom))
        captcha.save(captcha_img)

    def process_image(self):
        ' 处理图片，主要进行二值化，使得缺口形状和方块形状凸显出来，并分别剪裁为两张图片. '
        img = Image.open(captcha_img)
        img = img.convert('L')
        bw = img.point(lambda x: 0 if x < 190 else 255, '1')
        for region in [left_region, right_region]:
            crop_img = bw.crop(region)
            file_path = left_image if region[0] == 0 else right_image
            crop_img.save(file_path)

    def match(self):
        ' 模板匹配，找到缺口位置. '
        img_rgb = cv2.imread(left_image)
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        template = cv2.imread(right_image, 0)
        run = 1
        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        # 使用二分法查找阈值的精确值
        L = 0
        R = 1
        while run < 20:
            run += 1
            threshold = (R + L) / 2
            if threshold < 0:
                print('Error')
                return None
            loc = np.where(res >= threshold)
            if len(loc[1]) > 1:
                L += (R - L) / 2
            elif len(loc[1]) < 1:
                R -= (R - L) / 2
            elif len(loc[1]) == 1:
                return loc[1][0]

    def ease_out_quart(self, x):
        ' 路径算法. '
        return 1 - pow(1 - x, 4)

    def get_tracks(self, distance, seconds):
        ' 具体的移动轨迹. '
        tracks = [0]
        offsets = [0]
        for t in np.arange(0.0, seconds, 0.1):
            offset = round(self.ease_out_quart(t / seconds) * distance)
            tracks.append(offset - offsets[-1])
            offsets.append(offset)
        return offsets, tracks

    def move_to_gap(self):
        ' 移动到缺口位置. '
        distance = self.match() + 62
        offsets, tracks = self.get_tracks(distance, 5)
        slider = self.br.find_element_by_xpath('//div[@class="dvc-slider__handler"]')
        ActionChains(self.br).click_and_hold(slider).perform()
        for track in tracks:
            ActionChains(self.br).move_by_offset(xoffset=track, yoffset=random.randint(6, 10) / 10).perform()
        # 小幅晃动模拟人操作
        ActionChains(self.br).move_by_offset(xoffset=-3, yoffset=0).perform()
        ActionChains(self.br).move_by_offset(xoffset=3, yoffset=0).perform()
        ActionChains(self.br).move_by_offset(xoffset=2, yoffset=0).perform()
        ActionChains(self.br).move_by_offset(xoffset=-2, yoffset=0).perform()
        # 松开
        time.sleep(0.5)
        ActionChains(self.br).release().perform()

    def run(self):
        self.get_image()
        self.process_image()
        self.move_to_gap()

if __name__ == '__main__':
    url = 'https://callback.58.com/firewall/verifycode?' \
          'serialId=f096eef4eed0e73b2e72f3821270a6bf_134971c230e2457cbc05a0d0e8167b1a&' \
          'code=22&sign=7c671ef5adce913deff7718ee9f0a54d&' \
          'namespace=huangyelistpc&' \
          'url=https%3A%2F%2Finfo5.58.com%2Fcq%2Fshouji%2F%3FPGTID%3D0d100000-0002-50a7-5729-2f0e164d2c5f%26ClickID%3D4'
    c = CrackSlideCaptcha(url)
    c.run()