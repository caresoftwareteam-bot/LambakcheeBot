# -*- coding: utf-8 -*-
import sys, os, time, threading, tempfile, re
import PyQt5
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy
from PyQt5.QtGui import QMovie, QFont, QPixmap, QPainter, QColor, QFontDatabase
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
import cv2
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment, effects
from pydub.playback import play
from rapidfuzz import process, fuzz
from pythainlp.tokenize import word_tokenize
from ultralytics import YOLO
import numpy as np
import resources_rc
import fonts_rc

try:
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(
        os.path.dirname(PyQt5.__file__), 'Qt', 'plugins', 'platforms'
    )
except:
    pass

# ------------------- ChatBot Data -------------------
DEFAULT_ANSWER = "เชิญติดต่อร้อยเวรที่ห้องบริการประชาชนฝั่งซ้ายมือได้เลยค่ะ"

BROAD_WORDS = ["พันตำรวจ", "ร้อยตำรวจ", "ตำรวจ", "รอง", "สารวัตร", "ผู้กำกับ", "ผู้กอง", "ปราบปราม", "พลเอก", "พลตำรวจ"]

PREFIX_TO_REMOVE = ["มาหา", "มาขอพบ", "มาติดต่อ", "ขอพบ", "หา", "พบ", "มาพบ", "ไปพบ", "ขอเบอร์ติดต่อ",
                    "ขอทราบเบอร์ติดต่อ", "ทราบเบอร์ติดต่อ", "ขอเบอร์", "ทราบเบอร์", "ติดต่อ", "เบอร์", "โทร"]

BAD_WORDS = [
    # คำหยาบทั่วไป
    "กาก", "ไอ้สัส", "แม่ง", "อีดอก", "ชิบหาย", "จัญไร", "หี", "ควย", "จู๋", "เย็ด",
    "ปากหมา", "อีบ้า", "ไอ้ควาย", "ไอ้สัตว์",

    # คำลามก/อนาจาร
    "นม", "นมใหญ่", "หัวนม", "จิ๋ม", "หำ", "ก้น", "ตูด", "อมควย", "โม้ก", "สวิงกิ้ง",
    "สอดใส่", "แตกใน", "หีบาน", "เงี่ยน", "น้ำแตก", "ขย่ม", "เสียว", "สอด", "สอดใส่",
    "เยส", "xxx", "sex", "porn", "โป๊", "หนังโป๊",

    # คำเกี่ยวกับยาเสพติด
    "ยาเสพติด", "กัญชา", "เฮโรอีน", "โคเคน", "ยาบ้า", "ยาไอซ์", "มอร์ฟีน", "แมริฮวานา", "แอลเอสดี", "โคดีน", "ยาม้า",
    "ยา", "ไอซ์",

    # คำล่อ/อาชญากรรม
    "ลัก", "ขโมย", "ฆ่า", "แทง", "ทำร้าย", "ซ่อง", "โสเภณี"
]

police_info = {
    "ติดต่อแจ้งความคดี": "เชิญติดต่อร้อยเวรที่ห้องบริการประชาชนฝั่งซ้ายมือได้เลยค่ะ",
    "ต้องการเยี่ยมผู้ต้องหาที่ถูกจับ": "ขอเชิญติดต่อ เจ้าพนักงานควบคุมผู้ต้องหาได้ที่ห้องวิทยุ บริเวณชั้น 2 ของอาคารนี้",
    "ผู้ต้องหาได้เวลาไหนบ้าง": [
        "ช่วงเช้า  เวลา 08.00–09.00 น.",
        "ช่วงเที่ยง เวลา 12.00–13.00 น.",
        "ช่วงเย็น  เวลา 16.00–17.00 น."
    ],
    "ติดต่อขอรับรถจักรยานยนต์ที่ถูกยึด": "เชิญติดต่อร้อยเวรที่ห้องบริการประชาชนฝั่งซ้ายมือได้เลยค่ะ",
    "ติดต่อขอรับของกลางที่ถูกยึดคืน": "เชิญติดต่อเจ้าหน้าที่ห้องธุรการคดี ชั้น 2 ห้องในสุดได้เลยค่ะ",
    "มาพบร้อยเวรตามนัดหมาย": "เชิญติดต่อสอบถามร้อยเวรที่ห้องบริการประชาชนฝั่งซ้ายมือได้เลยค่ะ",
    "มาพบเจ้าหน้าที่": {
        "ติดต่อผู้กำกับสถานี/พันตำรวจเอกวุฒิไกร/ผู้กำกับต้อม": "เชิญที่บริเวณชั้น 2 ห้องในสุดได้เลยค่ะ",
        "ต้องการพบเจ้าหน้าที่สืบสวน": "เชิญติดต่อเจ้าหน้าที่สืบสวนบริเวณห้องสืบสวนที่นอกอาคาร ฝั่งขวามือเลยโรงจอดรถไปได้เลยค่ะ",
        "พันตำรวจโท.ณรงค์กร พรหมประสิทธิ์/รองผู้กำกับสืบสวน/รองต่อ": "เชิญติดต่อที่ห้องสืบสวน เดินออกจากอาคารไปทางขวามือเลยโรงจอดรถไปค่ะ",
        "พันตำรวจโท.พงศักดิ การรัตน์/รองผู้กำกับสอบสวน/รองโอ๋": [
            "หากนัดไว้แล้วเชิญติดต่อที่ห้องด้านหลังเคาเตอร์ประชาสัมพันธ์ ด้านขวาได้เลยค่ะ",
            "หากยังไม่ได้นัดหมายไว้เชิญติดต่อสอบถามร้อยเวรที่ห้องบริการประชาชนฝั่งซ้ายมือได้เลยค่ะ"
        ],
        "พันตำรวจตรี.ปรีชา เปีกบุตร/สารวัตรปรีชา/สารวัตรเปียก": [
            "หากนัดไว้แล้วเชิญติดต่อที่ห้องด้านหลังเคาเตอร์ประชาสัมพันธ์ ด้านซ้ายได้เลยค่ะ",
            "หากยังไม่ได้นัดหมายไว้เชิญติดต่อสอบถามร้อยเวรที่ห้องบริการประชาชนฝั่งซ้ายมือได้เลยค่ะ"
        ],
        "ร้อยตำรวจเอก.สุจิต มีนำพันธุ์/ผู้กองหมี": [
            "หากนัดไว้แล้วเชิญติดต่อที่ห้องด้านหลังเคาเตอร์ประชาสัมพันธ์ ด้านซ้ายได้เลยค่ะ",
            "หากยังไม่ได้นัดหมายไว้เชิญติดต่อสอบถามร้อยเวรที่ห้องบริการประชาชนฝั่งซ้ายมือได้เลยค่ะ"
        ],
        "ร้อยตำรวจเอกหญิง.พิมพิศา ก้องกิตติต์ไพศาล/ผู้กองหนิง/ผู้กองพิม": [
            "หากนัดไว้แล้วเชิญติดต่อที่ห้องด้านหลังเคาเตอร์ประชาสัมพันธ์ ด้านซ้ายได้เลยค่ะ",
            "หากยังไม่ได้นัดหมายไว้เชิญติดต่อสอบถามร้อยเวรที่ห้องบริการประชาชนฝั่งซ้ายมือได้เลยค่ะ"
        ],
        "พันตำรวจโท.ประยุทธ พึ่งเคหา/รองประยุทธ์": [
            "หากนัดไว้แล้วเชิญติดต่อบริเวณห้องชั้น 2 เดินขึ้นบันได เลี้ยวซ้ายห้องซ้ายมือ ได้เลยค่ะ",
            "หากยังไม่ได้นัดหมายไว้เชิญติดต่อสอบถามร้อยเวรที่ห้องบริการประชาชนฝั่งซ้ายมือได้เลยค่ะ"
        ],
        "พันตำรวจโท.พรทวี ชินนา/สารวัตรไข่": [
            "หากนัดไว้แล้วเชิญติดต่อบริเวณห้องชั้น 2 เดินขึ้นบันได เลี้ยวซ้ายห้องในสุด ได้เลยค่ะ",
            "หากยังไม่ได้นัดหมายไว้เชิญติดต่อสอบถามร้อยเวรที่ห้องบริการประชาชนฝั่งซ้ายมือได้เลยค่ะ"
        ],
        "พันตำรวจตรี.กษิดิ์เดช นิลลออ/สารวัตรยู้": [
            "หากนัดไว้แล้วเชิญติดต่อบริเวณห้องชั้น 2 เดินขึ้นบันได เลี้ยวซ้ายห้องซ้ายมือ ได้เลยค่ะ",
            "หากยังไม่ได้นัดหมายไว้เชิญติดต่อสอบถามร้อยเวรที่ห้องบริการประชาชนฝั่งซ้ายมือได้เลยค่ะ"
        ],
        "ร้อยตำรวจเอกหญิง.พลอยกินรี บุปผะโพธิ์/ผู้กองพลอย": [
            "หากนัดไว้แล้วเชิญติดต่อบริเวณห้องชั้น 2 เดินขึ้นบันได เลี้ยวซ้ายห้องซ้ายมือ ได้เลยค่ะ",
            "หากยังไม่ได้นัดหมายไว้เชิญติดต่อสอบถามร้อยเวรที่ห้องบริการประชาชนฝั่งซ้ายมือได้เลยค่ะ"
        ],
        "พันตำรวจโท.ธนากร จอมเกาะ/สารวัตรเติ้ล": [
            "หากนัดไว้แล้วเชิญติดต่อบริเวณห้องชั้น 3 เดินขึ้นบันได เลี้ยวซ้ายห้องซ้ายมือห้องที่ 2 ได้เลยค่ะ",
            "หากยังไม่ได้นัดหมายไว้เชิญติดต่อสอบถามร้อยเวรที่ห้องบริการประชาชนฝั่งซ้ายมือได้เลยค่ะ"
        ],
        "ร้อยตำรวจโท.บพิธพงศ์ เกาะลอย/ผู้หมวดต๊ะ": [
            "หากนัดไว้แล้วเชิญติดต่อบริเวณห้องชั้น 3 เดินขึ้นบันได เลี้ยวซ้ายห้องซ้ายมือห้องที่ 2 ได้เลยค่ะ",
            "หากยังไม่ได้นัดหมายไว้เชิญติดต่อสอบถามร้อยเวรที่ห้องบริการประชาชนฝั่งซ้ายมือได้เลยค่ะ"
        ],
        "พันตำรวจโท.อภิภู อินทร์ถา/สารวัตรสืบสวน/สารวัตรภู": "เชิญติดต่อห้องสืบสวน เดินออกจากอาคารไปทางขวามือเลยโรงจอดรถไปค่ะ",
        "พันตำรวจโท.อดุลย์ ยะท่าตุ้ม/สารวัตรจราจร/สารวัตรดุล": "เชิญติดต่อห้องจราจร ออกจากสถานีเดินทางไปขวามือ ตั้งอยู่เลยห้องสโมสร สนใลำผักชีไปทางขวามือค่ะ",
        "พันตำรวจโท.ภาคิน วงศ์สมศรี/สารวัตรอำนวยการ/สารวัตรศักดิ์": [
            "หากนัดไว้แล้วเชิญติดต่อบริเวณห้องชั้น 3 เดินขึ้นบันได เลี้ยวซ้ายห้องซ้ายมือห้องแรก ได้เลยค่ะ",
            "หากยังไม่ได้นัดหมายไว้ เชิญติดต่อสอบถามที่ห้องธุรการ ชั้น 3 ฝั่งขวามือค่ะ"
        ],
        "พันตำรวจโท.ณัฐพงษ์ กลิ่นลำยงค์/รองผู้กำกับป้องกันปราบปราม/รองน้อย": "ออกจากตัวอาคารเดินไปทางซ้ายมือ จะเจอห้องฝ่ายป้องกันปราบปราม ติดต่อเจ้าหน้าที่ด้านในได้เลยค่ะ",
        "พันตำรวจโท.ชวัลณัฐ ชูรัตน์/สารวัตรป้องกันปราบปารม/สารวัตรด้า": "ออกจากตัวอาคารเดินไปทางซ้ายมือ จะเจอห้องฝ่ายป้องกันปราบปราม ติดต่อเจ้าหน้าที่ด้านในได้เลยค่ะ",
        "พันตำรวจโท.มณฑล แดงสมิง/สารวัตรป้องกันปราบปราม/สารวัตรแดง": "ออกจากตัวอาคารเดินไปทางซ้ายมือ จะเจอห้องฝ่ายป้องกันปราบปราม ติดต่อเจ้าหน้าที่ด้านในได้เลยค่ะ",
        "พันตำรวจตรี.ชาติอาไนย เปรียบอภิชัย/สารวัตรป้องกันปราบปราม/สารวัตรแตงโม": "ออกจากตัวอาคารเดินไปทางซ้ายมือ จะเจอห้องฝ่ายป้องกันปราบปราม ติดต่อเจ้าหน้าที่ด้านในได้เลยค่ะ"
    },
    "อยู่หรือไหม": "เชิญติดต่อร้อยเวรที่ห้องบริการประชาชนบริเวณฝั่งซ้ายมือได้เลยค่ะ",
    "อยู่ไหม": "เชิญติดต่อร้อยเวรที่ห้องบริการประชาชนบริเวณฝั่งซ้ายมือได้เลยค่ะ",
    "แจ้งอุบัติเหตุ": "เชิญติดต่อร้อยเวรที่ห้องบริการประชาชนบริเวณฝั่งซ้ายมือได้เลยค่ะ",
    "ติดต่อเสียค่าปรับ/ชำระค่าปรับ": "เชิญติดต่อร้อยเวรที่ห้องบริการประชาชนฝั่งซ้ายมือได้เลยค่ะ",
    "ติดต่อขอใช้เครื่องขยายเสียง": "เชิญติดต่อเจ้าหน้าที่ตำรวจในห้องธุรการ บริเวณชั้น 3 ของสถานีค่ะ",
    "มาส่งเอกสาร": "เชิญติดต่อเจ้าหน้าที่ตำรวจในห้องธุรการ บริเวณชั้น 3 ของสถานีค่ะ",
    "ต้องการแจ้งเอกสารหาย": "เชิญติดต่อร้อยเวรที่ห้องบริการประชาชนบริเวณฝั่งซ้ายมือได้เลยค่ะ",
    "ต้องการลงประจำวัน": "เชิญติดต่อร้อยเวรที่ห้องบริการประชาชนบริเวณฝั่งซ้ายมือได้เลยค่ะ",
    "ข้อมูลบริการ/ห้อง": {
        "ติดต่อขอต่อใบสำคัญประจำตัวคนต่างด้าว,ต่างชาติ": "เชิญติดต่อเจ้าหน้าที่ตำรวจในห้องธุรการ บริเวณชั้น 3 ของสถานีค่ะ",
        "ติดต่อแจ้งที่อยู่คนต่างด้าว,ต่างชาติ": "เชิญติดต่อเจ้าหน้าที่ตำรวจในห้องธุรการ บริเวณชั้น 3 ของสถานีค่ะ",
        "ติดต่อทำเรื่องขออยู่ต่อของคนต่างด้าว,ต่างชาติ": "เชิญติดต่อเจ้าหน้าที่ตำรวจในห้องธุรการ บริเวณชั้น 3 ของสถานีค่ะ",
        "ห้องจราจรอยู่ที่ไหน/ห้องจราจรอยู่ไหน/ห้องจราจรอยู่ตรงไหน/แผนกจราจรอยู่ไหน/จราจรอยู่ไหน": "ออกจากสถานีไปทางขวามือ ตั้งอยู่เลยห้องสโมสร สน.ลำผักชีไปทางขวามือค่ะ",
        "ห้องฝ่ายป้องกันปราบปรามอยู่ที่ไหน/ห้องป้องกันปราบปรามอยู่ไหน/ฝ่ายปราบปรามอยู่ไหน/ห้องปราบปรามอยู่ไหน": "ออกจากตัวอาคารไปทางซ้ายมือ จะเจอห้องฝ่ายป้องกันปราบปราม",
        "ห้องน้ำอยู่ที่ไหน/ห้องน้ำไปทางไหน/ห้องน้ำอยู่ไหน/ห้องน้ำอยู่ตรงไหน": "เดินออกจากอาคารไปทางซ้ายแล้วเลี้ยวซ้ายตรงเข้าไปสุดทางเดินได้เลยค่ะ"
    },
    "ติดต่อศูนย์ไกล่เกลี่ยข้อพิพาท": [
        "หากนัดเจ้าหน้าที่ไว้แล้วติดต่อศูนย์ไกล่เกลี่ยบริเวณห้องด้านหลังเคาน์เตอร์ประชาสัมพันธ์ได้เลยค่ะ",
        "หากยังไม่ได้นัดหมายเชิญติดต่อสอบถามร้อยเวรที่ห้องบริการประชาชนบริเวณฝั่งซ้ายมือได้เลยค่ะ"
    ],
    "ขอทราบเบอร์ติดต่อ": {
        "ผู้กำกับสถานี/พันตำรวจเอกวุฒิไกร/ผู้กำกับต้อม": "เบอร์ติดต่อ พันตำรวจเอกวุฒิไกร จตุรงค์เสรีกุล (ผู้กำกับสถานี) 083-828-5557",
        "ผู้บังคับการตำรวจนครบาล 3/พันตำรวจตรี.เกียรติกุล สนธิเณร/ผู้การปั๋ม": "เบอร์ติดต่อ พันตำรวจตรีเกียรติกุล สนธิเณร (ผู้บังคับการตำรวจนครบาล 3) โทร 081-305-1200",
        "พันตำรวจโท.ณรงค์กร พรหมประสิทธิ์/รองผู้กำกับสืบสวน/รองต่อ": "เบอร์ติดต่อ พันตำรวจโท.ณรงค์กร พรหมประสิทธิ์ 089-183-9000",
        "สน.ลำผักชี": "เบอร์ติดต่อ สน.ลำผักชี 02-186-0123",
        "พันตำรวจโท.พงศักดิ์ การรัตน์/รองผู้กำกับสอบสวน/รองโอ๋": "เบอร์ติดต่อ พันตำรวจโท.พงศักดิ์ การรัตน์ 086-398-0430",
        "พันตำรวจโท.ประยุทธ พึ่งเคหา/รองประยุทธ": "เบอร์ติดต่อ พันตำรวจโท.ประยุทธ พึ่งเคหา 091-153-6666",
        "พันตำรวจโท.ณัฐพงษ์ กลิ่นลำยงค์/รองผู้กำกับฝ่ายป้องกันปราบปราม/รองน้อย": "เบอร์ติดต่อ พันตำรวจโท.ณัฐพงษ์ กลิ่นลำยงค์ 081-354-2939",
        "พันตำรวจโท.พรทวี ชินนา/สารวัตรไข่": "เบอร์ติดต่อ พันตำรวจโท.พรทวี ชินนา 084-094-9352",
        "พันตำรวจตรี.กษิดิ์เดช นิลลออ/สารวัตรยู้": "เบอร์ติดต่อ พันตำรวจตรี.กษิดิ์เดช นิลลออ 086-333-1524",
        "ร้อยตำรวจเอกหญิง.พลอยกินรี บุปผะโพธิ์/ผู้กองพลอย": "เบอร์ติดต่อ ร้อยตำรวจเอกหญิง.พลอยกินรี บุปผะโพธิ์ 089-653-3339",
        "พันตำรวจโท.ธนากร จอมเกาะ/สารวัตรเติ้ล": "เบอร์ติดต่อ พันตำรวจโท.ธนากร จอมเกาะ 093-329-2357",
        "ร้อยตำรวจโท.บพิธพงศ์ เกาะลอย/ผู้หมวดต๊ะ": "เบอร์ติดต่อ ร้อยตำรวจโท.บพิธพงศ์ เกาะลอย 089-634-4338",
        "พันตำรวจโท.อภิภู อินทร์ถา/สารวัตรสืบสวน/สารวัตรภู": "เบอร์ติดต่อ พันตำรวจโท.อภิภู อินทร์ถา 097-218-6375",
        "พันตำรวจโท.อดุลย์ ยะท่าตุ้ม/สารวัตรจราจร/สารวัตรดุล": "เบอร์ติดต่อ พันตำรวจโท.อดุลย์ ยะท่าตุ้ม 081-936-0506",
        "พันตำรวจโท.ภาคิน วงศ์สมศรี/สารวัตรอำนวยการ/สารวัตรศักดิ์": "เบอร์ติดต่อ พันตำรวจโท.ภาคิน วงศ์สมศรี 087-719-4384",
        "พันตำรวจโท.ชวัลณัฐ ชูรัตน์/สารวัตรป้องกันปราบปราม/สารวัตรด้า": "เบอร์ติดต่อ พันตำรวจโท.ชวัลณัฐ ชูรัตน์ 081-407-4513",
        "พันตำรวจโท.มณฑล แดงสมิง/สารวัตรป้องกันปราบปราม/สารวัตรแดง": "เบอร์ติดต่อ พันตำรวจโท.มณฑล แดงสมิง 081-142-5519",
        "พันตำรวจตรี.ชาติอาไนย เปรียบอภิชัย/สารวัตรป้องกันปราบปราม/สารวัตรแตงโม": "เบอร์ติดต่อ พันตำรวจตรี.ชาติอาไนย เปรียบอภิชัย 061-592-4452"
    }
}

# ------------------- Functions -------------------
def is_too_broad(text: str) -> bool:
    for pre in PREFIX_TO_REMOVE:
        text = re.sub(rf"^{pre}", "", text).strip()
    for bw in BROAD_WORDS:
        if text == bw or text.startswith(bw + " "):
            return True
    return False


def normalize(text: str) -> str:
    return text.lower().strip()


def expand_contacts(contacts: dict) -> dict:
    expanded = {}
    for k in contacts.keys():
        parts = k.split("/")
        for p in parts:
            key = normalize(p)
            expanded[key] = k
    return expanded


def contains_bad_word(text: str) -> bool:
    words = word_tokenize(normalize(text))
    return any(w in BAD_WORDS for w in words)


def find_contact(name_only: str, contacts: dict) -> str | None:
    expanded = expand_contacts(contacts)
    query = normalize(name_only)

    # exact match กับ alias
    if query in expanded:
        return contacts[expanded[query]]

    # fuzzy match
    best = process.extractOne(query, expanded.keys(), scorer=fuzz.partial_ratio, score_cutoff=60)
    if best:
        return contacts[expanded[best[0]]]

    return None


def format_answer(answer, question):
    if isinstance(answer, list):
        return "\n".join(answer)
    return answer

def check_location_or_service(question_norm: str) -> str | None:
    info_dict = police_info.get("ข้อมูลบริการ/ห้อง", {})

    best_match = None
    best_score = 0

    for k, answer in info_dict.items():
        aliases = [alias.lower().strip() for alias in k.split("/")]

        for alias in aliases:
            if question_norm == alias:
                return answer

            score = fuzz.ratio(alias, question_norm)
            if score > best_score:
                best_score = score
                best_match = answer

    if best_score >= 80:
        return best_match

    return None

def ask_bot(question: str) -> str:
    question_norm = normalize(question)

    keys_exact = {normalize(k): k for k in police_info.keys()
                  if k not in ["มาพบเจ้าหน้าที่", "ขอทราบเบอร์ติดต่อ",
                               "ผู้ต้องหาได้เวลาไหนบ้าง", "ต้องการเยี่ยมผู้ต้องหาที่ถูกจับ"]}
    if question_norm in keys_exact:
        return format_answer(police_info[keys_exact[question_norm]], question_norm)

    # 1. ตรวจ broad term
    if all(word in BROAD_WORDS for word in word_tokenize(question_norm)):
        return DEFAULT_ANSWER

    # 2. ตรวจคำหยาบ
    if contains_bad_word(question_norm):
        return "ขอโทษค่ะ ฉันไม่สามารถตอบคำถามเกี่ยวกับเรื่องนี้ได้"

    # 3. คำถามเกี่ยวกับเบอร์โทร
    if "เบอร์" in question_norm or "โทร" in question_norm:
        # คำถามทั่วไปที่ไม่ได้ระบุชื่อ
        no_name_queries = [
            "ขอเบอร์", "เบอร์", "โทร", "ขอเบอร์ติดต่อ",
            "ขอทราบเบอร์ติดต่อ", "เบอร์ติดต่อ", "เบอร์โทร"
        ]

        if question_norm in no_name_queries:
            print("1111")
            return DEFAULT_ANSWER

        contacts = police_info.get("ขอทราบเบอร์ติดต่อ", {})

        # ลอง match โดยตรง + alias/fuzzy
        result = find_contact(normalize(question_norm), contacts)
        if result:
            return result

        # ลบ prefix แล้ว match อีกครั้ง
        name_only = question_norm.strip()
        for prefix in PREFIX_TO_REMOVE:
            name_only = re.sub(rf"^{prefix}", "", name_only).strip()

        if not name_only or is_too_broad(name_only):
            return DEFAULT_ANSWER

        # ใช้ normalize และ expand alias ใน find_contact
        result = find_contact(normalize(name_only), contacts)
        return result or DEFAULT_ANSWER

    if "สวัสดี" in question_norm:
        return "สวัสดีค่ะ สน.ลำผักชียินดีต้อนรับค่ะ"
    if "เวลา" in question_norm or "เวลาเยี่ยม" in question_norm:
        return format_answer(police_info.get("ผู้ต้องหาได้เวลาไหนบ้าง"), question_norm)
    if "เยี่ยม" in question_norm:
        return format_answer(police_info.get("ต้องการเยี่ยมผู้ต้องหาที่ถูกจับ"), question_norm)
    if "ไกล่เกลี่ย" in question_norm:
        return format_answer(police_info.get("ติดต่อศูนย์ไกล่เกลี่ยข้อพิพาท"), question_norm)
    if "เครื่องขยายเสียง" in question_norm:
        return format_answer(police_info.get("ติดต่อขอใช้เครื่องขยายเสียง"), question_norm)

    result = check_location_or_service(question_norm)
    if result:
        return result

    # 4. คำถามพบเจ้าหน้าที่
    if any(k in question_norm for k in ["ติดต่อ", "มาพบ", "ไปพบ", "ติดต่อ"]):
        if question_norm.strip() in ["ติดต่อ", "พบ", "ไปพบ", "มาพบ"]:
            return DEFAULT_ANSWER

        officers = police_info.get("มาพบเจ้าหน้าที่", {})
        name_only = question_norm.strip()
        if not name_only or is_too_broad(name_only):
            return DEFAULT_ANSWER
        expanded = expand_contacts(officers)
        if name_only in expanded:
            return format_answer(officers[expanded[name_only]], question_norm)
        if len(name_only) >= 3:
            best = process.extractOne(name_only, expanded.keys(), scorer=fuzz.partial_ratio, score_cutoff=70)
            if best:
                return format_answer(officers[expanded[best[0]]], question_norm)
        # ถ้าไม่เจอเจ้าหน้าที่ → DEFAULT
        return DEFAULT_ANSWER

    # 5. ข้อความอื่น ๆ เช่น สวัสดี, เวลา, เยี่ยม, ไกล่เกลี่ย

    return DEFAULT_ANSWER

# ------------------- TTS -------------------
is_speaking_flag = False
retry_silent = False
speak_lock = threading.Lock()

def speak(text: str, speed: float = 1.2):
    global is_speaking_flag
    with speak_lock:
        if is_speaking_flag:
            return
        is_speaking_flag = True

    tmp_path = os.path.join(tempfile.gettempdir(), "temp_speech.mp3")
    try:
        tts = gTTS(text=text, lang='th')
        tts.save(tmp_path)

        sound = AudioSegment.from_file(tmp_path, format="mp3")
        sound = effects.strip_silence(sound, silence_len=100, silence_thresh=-40)

        new_rate = int(sound.frame_rate * speed)
        sound = sound._spawn(sound.raw_data, overrides={"frame_rate": new_rate})
        sound = sound.set_frame_rate(44100)

        play(sound)

    except Exception as e:
        print("TTS/Play error:", e)

    finally:
        is_speaking_flag = False
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def speak_async(text: str, speed: float = 1.2):
    threading.Thread(target=speak, args=(text, speed), daemon=True).start()

# ------------------- Listen -------------------
def listen_from_mic(update_text_callback, status_callback, stop_event: threading.Event = None):
    global retry_silent
    r = sr.Recognizer()
    r.dynamic_energy_threshold = True
    r.pause_threshold = 0.8

    try:
        mic = sr.Microphone()  # กำหนด index ชัดเจน
    except Exception as e:
        return None

    status_callback("preparing")
    speak("กรุณารอสักครู่ค่ะ กำลังเตรียมการฟัง")
    while is_speaking_flag:
        time.sleep(0.5)

    with mic as source:
        r.adjust_for_ambient_noise(source, duration=2)
        # print("Energy threshold set to:", r.energy_threshold)

    speak("พร้อมรับฟังแล้วค่ะ กรุณาพูดได้เลย")
    while is_speaking_flag:
        time.sleep(0.5)
    retry_silent = False

    with mic as source:
        while True:
            if stop_event and stop_event.is_set():
                return None

            status_callback("listening")
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=8)
            except sr.WaitTimeoutError:
                update_text_callback("ไม่พบเสียง กรุณาพูดอีกครั้งคะ")
                if not retry_silent:
                    speak("ขอโทษค่ะ ไม่พบเสียงพูด กรุณาพูดอีกครั้งนะคะ")
                    retry_silent = True
                continue

            try:
                text_partial = r.recognize_google(audio, language="th-TH")
                update_text_callback(f"คุณพูดว่า: {text_partial}")
                time.sleep(2)
                retry_silent = False
                return text_partial
            except sr.UnknownValueError:
                update_text_callback("ได้ยินไม่ชัด กรุณาพูดอีกครั้งคะ")
                if not retry_silent:
                    speak("ขอโทษค่ะ ได้ยินไม่ชัด กรุณาพูดอีกครั้งนะคะ")
                    retry_silent = True
                continue

# ------------------- Listener Thread -------------------
class ListenerThread(QThread):
    new_question = pyqtSignal(str)
    new_answer = pyqtSignal(object)
    status_text = pyqtSignal(str)

    def run(self):
        while True:
            q = listen_from_mic(self.new_question.emit, self.status_text.emit)
            if not q:
                continue
            self.new_question.emit(q)
            answer = ask_bot(q)
            self.new_answer.emit(answer)
            speak(answer)


# ------------------- Camera Detection -------------------
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

class CameraThread(QThread):
    greet_signal = pyqtSignal(str)
    frame_signal = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.model = None
        self.has_greeted = False
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        if self.model is None:
            self.model = YOLO("yolov8n.pt")
            self.model.verbose = False

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Cannot open camera")
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

        empty_count = 0

        while self._running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            self.frame_signal.emit(frame.copy())

            small_frame = cv2.resize(frame, (640, 480))
            results = self.model.predict(
                small_frame,
                conf=0.5,
                classes=[0],
                verbose=False,
                show=False,
                device="cpu"
            )

            dets = []
            for r in results:
                if r.boxes is None:
                    continue
                for box in r.boxes.xyxy.cpu().numpy():
                    dets.append(box)

            current_people = [(int((x1 + x2) / 2), int((y1 + y2) / 2)) for (x1, y1, x2, y2) in dets]

            if len(current_people) > 0:
                empty_count = 0
                if not self.has_greeted:
                    self.has_greeted = True
                    self.greet_signal.emit("ติดต่อสอบถามข้อมูลเชิญทางนี้ค่ะ")
                    speak_async("ติดต่อสอบถามข้อมูลเชิญทางนี้ค่ะ")
            else:
                empty_count += 1
                if empty_count >= 5:
                    # เมื่อคนหายไปนานพอ ให้สามารถพูดได้อีกครั้ง
                    self.has_greeted = False
                    empty_count = 0

            time.sleep(0.05)

        cap.release()

            # วาด bounding box
        #     for (x1, y1, x2, y2) in dets:
        #         cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        #
        #     # แสดงหน้าต่าง popup ของ OpenCV
        #     cv2.imshow("Camera Detection", frame)
        #     if cv2.waitKey(1) & 0xFF == ord('q'):
        #         break
        #
        # cap.release()
        # cv2.destroyAllWindows()


# ------------------- Main GUI -------------------
class MainBot(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LampakcheeBot")
        self.showFullScreen()
        self.setStyleSheet("background-color: black; color: white;")
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(20, 20, 0, 0)
        self.status_icon = QLabel(self)
        self.icon_size = 120
        self.status_icon.setFixedSize(self.icon_size, self.icon_size)
        self.set_status_icon("loading", self.icon_size)
        top_layout.addWidget(self.status_icon, alignment=Qt.AlignLeft | Qt.AlignTop)
        top_layout.addStretch()
        main_layout.addLayout(top_layout)
        gif_layout = QHBoxLayout()
        self.gif_label = QLabel(self)
        self.gif_label.setAlignment(Qt.AlignCenter)

        self.movie = QMovie(":/eyes_tanuki_idle.gif")
        self.movie.setScaledSize(QSize(1000, 600))
        self.gif_label.setMovie(self.movie)
        self.movie.start()
        gif_layout.addStretch()
        gif_layout.addWidget(self.gif_label)
        gif_layout.addStretch()
        main_layout.addLayout(gif_layout, stretch=2)
        main_layout.setAlignment(gif_layout, Qt.AlignTop)

        self.text_label = QLabel(self)
        self.text_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.text_label.setMinimumHeight(200)
        self.text_label.setStyleSheet("color: #FFF8B0;")
        self.text_label.setWordWrap(True)
        self.text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        main_layout.addWidget(self.text_label, stretch=1)
        self.adjust_font()

        # ---------------- Small camera overlay ----------------
        self.camera_overlay = QLabel(self)
        self.camera_overlay.setFixedSize(200, 150)  # ขนาดกล้องเล็ก
        self.camera_overlay.move(self.width() - 220, 20)  # มุมขวาบน
        self.camera_overlay.setStyleSheet("border: 2px solid yellow;")
        self.camera_overlay.setAttribute(Qt.WA_TranslucentBackground)
        self.camera_overlay.setScaledContents(True)  # ให้ QLabel scale ภาพ
        self.camera_overlay.raise_()  # อยู่เหนือ widget อื่น

        self.listener = ListenerThread()
        self.listener.new_question.connect(self.on_new_question)
        self.listener.new_answer.connect(self.on_new_answer)
        self.listener.status_text.connect(self.on_status_text)
        self.listener.start()

        self.camera = CameraThread()
        self.camera.greet_signal.connect(self.on_greet)
        self.camera.frame_signal.connect(self.update_small_camera)  # ใช้ signal แทน timer + cap_small
        self.camera.start()

    def update_small_camera(self, frame):
        frame_small = cv2.resize(frame, (self.camera_overlay.width(), self.camera_overlay.height()))
        frame_small = cv2.cvtColor(frame_small, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_small.shape
        bytes_per_line = ch * w
        qt_image = PyQt5.QtGui.QImage(frame_small.data, w, h, bytes_per_line, PyQt5.QtGui.QImage.Format_RGB888)
        self.camera_overlay.setPixmap(QPixmap.fromImage(qt_image))

    def adjust_font(self):
        screen_height = self.screen().size().height()
        font_size = int(screen_height * 0.05)
        # โหลดฟ้อนต์
        font_id = QFontDatabase.addApplicationFont(":/fonts/TH Chakra Petch Bold.ttf")
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]

        # ตั้งค่าให้ QLabel
        self.text_label.setFont(QFont(font_family, font_size, QFont.Bold))

    def set_status_icon(self, state, size=50):
        if state == "preparing":
            pix = QPixmap(":/icons/loading.png")
        elif state == "listening":
            pix = QPixmap(":/icons/mic.png")
        elif state == "processing":
            pix = QPixmap(":/icons/processing.png")
        else:
            pix = QPixmap(":/icons/thinking.png")

        white_pix = QPixmap(pix.size())
        white_pix.fill(Qt.transparent)
        painter = QPainter(white_pix)
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.drawPixmap(0, 0, pix)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(white_pix.rect(), QColor("#FFF8B0"))
        painter.end()

        self.status_icon.setPixmap(
            white_pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    # ---------- Slot ----------
    def on_new_question(self, text):
        self.set_label_text(text)

    def on_new_answer(self, text):
        self.set_label_text(f"{text}")
        self.set_status_icon("idle", self.icon_size)

    def on_status_text(self, state):
        if state in ["preparing", "listening", "processing"]:
            self.set_status_icon(state, self.icon_size)

    # ---------- Core ----------
    def set_label_text(self, text):
        if isinstance(text, list):
            final_lines = text
        else:
            max_chars = 40
            final_lines = []
            current_line = ""
            for ch in text:
                if len(current_line) + 1 > max_chars:
                    final_lines.append(current_line)
                    current_line = ch
                else:
                    current_line += ch
            if current_line:
                final_lines.append(current_line)

        text = "".join(final_lines)
        clean_text = text.replace("\n ", "\n").replace(" \n", "\n")
        self.text_label.setText(clean_text)

    def on_greet(self, text):
        global is_speaking_flag
        # print(f"Is_speak (before thread): {is_speaking_flag}")
        if not is_speaking_flag:
            threading.Thread(target=speak, args=(text,)).start()


# ------------------- Run App -------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    bot = MainBot()
    bot.show()
    sys.exit(app.exec_())