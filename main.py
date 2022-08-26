import win32gui, win32con, win32api
import sys, os, json
import aircv as ac
import numpy as np
from pymysql import *
from PIL import Image, ImageTk
from PyQt5.QtWidgets import QApplication
import tkinter as tk
import tkinter.filedialog


class iconDetector:
    def __init__(self):
        self.window = None
        self.src_dir = './src'
        self.shishen = json.loads(open('./shishen.json', 'rb').read())
        self.table_name = None

    def getWindow(self):
        window = win32gui.FindWindow(0, '阴阳师-网易游戏')
        self.window = window
        return window

    def windowCorrection(self):
        self.window = self.getWindow()
        win32gui.SetWindowPos(self.window,
                              win32con.HWND_TOPMOST,
                              0, 0, 1280, 720,
                              win32con.SWP_SHOWWINDOW)
        left, top, right, bottom = win32gui.GetWindowRect(self.window)
        print('width', right, 'height', bottom, 'top', top, 'left', left)

    def imageShot(self):
        window = self.getWindow()
        app = QApplication(sys.argv)
        screen = QApplication.primaryScreen()
        img = screen.grabWindow(window).toImage()
        img.save('screenshot.jpg')
        return img

    def query(self, M, D):
        query = 'select * from ' + self.table_name
        query_list = []
        for m in M:
            if m != '':
                query_list.append("(m1 = '%s' or m2 = '%s' or m3 = '%s' or m4 = '%s' or m5 = '%s')"
                                  % (m, m, m, m, m))
        for d in D:
            if d != '':
                query_list.append("(d1 = '%s' or d2 = '%s' or d3 = '%s' or d4 = '%s' or d5 = '%s')"
                                  % (d, d, d, d, d))
        if query_list != []:
            query += ' where ' + ' and '.join(query_list)
        return query

    def sql_query(self, M, D):
        conn = connect(host='localhost', port=3306, user='root', password='chenjian', database='yys_data',
                       charset='gbk')
        cursor = conn.cursor()
        cursor.execute(self.query(M, D))
        result = cursor.fetchall()
        conn.commit()
        cursor.close()
        result_list = [int(item[-1]) for item in result]
        return sum(result_list), len(result_list)

    def imageDetect(self, imsrc, save_dir, confidence=0.7):
        result_list = []
        for image_name in os.listdir(self.src_dir):
            imdir = self.src_dir + '//' + image_name
            imobj = ac.imread(imdir)
            match_result = ac.find_all_template(imsrc, imobj, confidence)
            for result in match_result:
                x, y = result['result']
                shishen_name = self.shishen[image_name.split('_')[0]]['name']
                result_list.append((shishen_name, x, y, imdir))
        result_list.sort(key=lambda x: x[1])
        while len(result_list) > 5:
            for i in range(1, len(result_list)):
                if result_list[i][1] - result_list[i-1][1] < 70:
                    del result_list[i]
                    break
        shishen_list = [item[0] for item in result_list]
        image_list = [item[-1] for item in result_list]
        image = np.array(Image.open(image_list[0]).convert('RGB'))
        for i in range(1, len(image_list)):
            image = np.concatenate((image, np.array(Image.open(image_list[i]).convert('RGB'))), axis=1)
        print(shishen_list)
        Image.fromarray(image).save(save_dir)
        assert len(shishen_list) == 5
        return tuple(shishen_list), image

    def detect(self, confidence=0.70, imsrc=None):
        if imsrc is None:
            self.windowCorrection()
            self.imageShot()
            imsrc = ac.imread('./screenshot.jpg')
        #imsrc = ac.imread('./false3.jpg')[:90, :, :]

        M, M_image = self.imageDetect(imsrc[:90, :600, :], 'M.jpg')
        D, D_image = self.imageDetect(imsrc[:90, 600:, :], 'D.jpg')

        if '心狩鬼女红叶' in M or '心狩鬼女红叶' in D:
            self.table_name = 'data_2022_07_27'
        else:
            self.table_name = 'data_2022_06_22'
        win, tot = self.sql_query(M, D)
        print(win, tot)
        if tot == 0:
            result = 'No Game. No Gambling'
        elif win / tot <= 0.4:
            result = 'Right Win.\tWin Rate: %.4f' %(win / tot)
        elif win / tot >= 0.6:
            result = 'Left Win.\tWin Rate: %.4f' % (win / tot)
        else:
            result = 'It is a Tie\tWin Rate: %.4f' % (win / tot)
        return M_image, D_image, result


if __name__ == '__main__':
    model = iconDetector()
    # model.detect()
    window = tk.Tk()
    window.title('yys-detector')
    window.geometry('400x230')

    def show(result):
        global M_img, D_img
        global M_label, D_label, result_label
        M_img = ImageTk.PhotoImage(Image.open('M.jpg'))
        D_img = ImageTk.PhotoImage(Image.open('D.jpg'))
        M_label = tk.Label(window, image=M_img)
        M_label.place(x=10, y=50, width=325, height=65)
        D_label = tk.Label(window, image=D_img)
        D_label.place(x=10, y=130, width=325, height=65)
        result_label = tk.Label(window, text=result)
        result_label.place(x=10, y=200)
        window.update()

    def clear():
        try:
            M_label.destroy()
            D_label.destroy()
            result_label.destroy()
        except:
            pass

    def startScreen():
        clear()
        M_image, D_image, result = model.detect()
        show(result)

    def startImage():
        clear()
        imdir = tkinter.filedialog.askopenfilename()
        imsrc = ac.imread(imdir)
        M_image, D_image, result = model.detect(imsrc=imsrc)
        show(result)

    tk.Button(window, activebackground='red', text='实时识别', width=10, command=startScreen).grid(row=2, column=1, sticky='nw', padx=10, pady=5)
    tk.Button(window, activebackground='red', text='本地识别', width=10, command=startImage).grid(row=2, column=1, sticky='nw', padx=100, pady=5)

    window.mainloop()