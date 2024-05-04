import re
import pygame
import time
import sys
import os
import psutil
import pytesseract
import pyautogui
import json
from PIL import ImageGrab
from PIL import Image
from skimage.metrics import structural_similarity as ssim
from skimage.transform import resize
import numpy as np
from pynput.keyboard import Key, Listener

pygame.init()

assets_folder = "assets"
attributes_folder = "assets"

attributes = {
    "attack": os.path.join(attributes_folder, "attack.png"),
    "crit": os.path.join(attributes_folder, "crit.png"),
    "fury": os.path.join(attributes_folder, "fury.png"),
    "evasion": os.path.join(attributes_folder, "evasion.png"),
    "regen": os.path.join(attributes_folder, "regen.png"),
    "injury": os.path.join(attributes_folder, "injury.png"),
    "shield": os.path.join(attributes_folder, "shield.png"),
    "poison": os.path.join(attributes_folder, "poison.png"),
    "frost": os.path.join(attributes_folder, "frost.png"),
    "ward": os.path.join(attributes_folder, "ward.png"),
    "ulti": os.path.join(attributes_folder, "ulti.png"),
    "health": os.path.join(attributes_folder, "health.png"),
}

attributes_area = (1510, 885, 35, 33)

screen_width, screen_height = 600, 250
screen = pygame.display.set_mode((screen_width, screen_height))

WHITE = (255, 255, 255)

title_font_size = 30
description_font_size = 16
font = pygame.font.SysFont(None, description_font_size)
title_font = pygame.font.SysFont(None, title_font_size)

running = False
dota_running = False

toggle_sound = pygame.mixer.Sound("switch.wav")


def read_text_from_screen(region):
    screenshot = ImageGrab.grab(region)
    text = pytesseract.image_to_string(screenshot)
    return text.strip()


def extract_numbers(text):
    numbers = re.findall(r"\d+", text)
    return numbers


def preprocess_images():
    scaled_attributes = {}
    target_size = (40, 33)

    for attribute_name, attribute_path in attributes.items():
        attribute_image = pygame.image.load(attribute_path)
        scaled_image = pygame.transform.scale(attribute_image, target_size)
        scaled_attributes[attribute_name] = scaled_image

    return scaled_attributes


scaled_attributes = preprocess_images()

lock_button_clicked = False


def wait_until_balance_grows():
    global lock_button_clicked
    while True:
        balance_region = (940, 1010, 1000, 1050)
        balance_text = read_text_from_screen(balance_region)
        balance_numbers = extract_numbers(balance_text)
        balance = int(balance_numbers[0]) if balance_numbers else 0

        if balance and balance >= 1000 and lock_button_clicked:
            lock_button_clicked = False
            break

        if not lock_button_clicked:
            pyautogui.click(1262, 821)
            lock_button_clicked = True

        if lock_button_clicked:
            pyautogui.click(1262, 621)

        time.sleep(1)


def match_attribute(image):
    max_ssim = -1
    best_match = "Unknown"
    for attribute_name, attribute_path in attributes.items():
        attribute_surface = pygame.image.load(attribute_path).convert_alpha()
        attribute_surface = pygame.transform.scale(attribute_surface, image.get_size())
        attribute_array = pygame.surfarray.array3d(attribute_surface)
        image_array = pygame.surfarray.array3d(image)

        win_size = min(image.get_width(), image.get_height()) // 10
        similarity = ssim(
            image_array, attribute_array, win_size=win_size, multichannel=True
        )

        if similarity > max_ssim:
            max_ssim = similarity
            best_match = attribute_name

    return best_match


def check_character_attributes():
    screenshot = pyautogui.screenshot(region=attributes_area)
    screenshot_surface = pygame.image.fromstring(
        screenshot.tobytes(), screenshot.size, screenshot.mode
    )
    attribute_name = match_attribute(screenshot_surface)
    pygame.image.save(screenshot_surface, "attribute.png")
    return attribute_name


def buy_spell(x, y, attribute_name):
    pyautogui.click(x, y)


spells_bought_this_cycle = [False, False, False]


def refresh_spells():
    refresh_button_coordinates = (1264, 657)
    pyautogui.click(refresh_button_coordinates)


def match_spells_with_attribute(
    current_spells, attribute_name, spells_bought_this_cycle
):
    filename = f"spells/{attribute_name}.json"

    time.sleep(0.3)

    with open(filename, "r") as f:
        spells_data = json.load(f)

    cleaned_current_spells = [
        re.sub(r"[^\w\s|]", "", spell.strip().lower().replace("|", ""))
        for spell in current_spells
    ]

    relevant_spells = []

    for category, spells in spells_data.items():
        for spell in spells:
            cleaned_spell = re.sub(r"[^\w\s-]", "", spell.strip().lower())
            if cleaned_spell in cleaned_current_spells:
                relevant_spells.append(spell)

    attribute1_region = (550, 772, 700, 792)
    attribute2_region = (768, 772, 938, 792)
    attribute3_region = (1006, 772, 1180, 792)

    balance_region = (940, 1010, 1000, 1050)
    balance_text = read_text_from_screen(balance_region)
    balance_numbers = extract_numbers(balance_text)
    balance = int(balance_numbers[0]) if balance_numbers else 0

    waiting = False

    print(balance)
    print(attribute_name, attributes)

    for idx, spell_bought in enumerate(spells_bought_this_cycle):
        if not spell_bought:
            if idx < len(relevant_spells):
                cleaned_current_spells = [
                    re.sub(
                        r"[^\w\s-]",
                        "",
                        spell.strip().lower().replace(" ", "").replace("|", ""),
                    )
                    for spell in current_spells
                ]

                cleaned_relevant = [
                    re.sub(
                        r"[^\w\s-]",
                        "",
                        spell.strip().lower().replace(" ", "").replace("|", ""),
                    )
                    for spell in relevant_spells[idx]
                ]

                cleaned_relevant = "".join(cleaned_relevant)

                spell_index = next(
                    (
                        i
                        for i, spell in enumerate(cleaned_current_spells)
                        if spell in cleaned_relevant
                    ),
                    -1,
                )

                x, y = (
                    [attribute1_region, attribute2_region, attribute3_region][
                        spell_index
                    ][0],
                    [attribute1_region, attribute2_region, attribute3_region][
                        spell_index
                    ][1],
                )

                if balance >= 1100:
                    buy_spell(x, y, current_spells[spell_index])
                    waiting = False
                    spells_bought_this_cycle[idx] = True
                elif balance <= 1100:
                    wait_until_balance_grows()
                    waiting = True

    if not waiting and balance >= 1020 and not lock_button_clicked:
        refresh_spells()
        spells_bought_this_cycle = [False, False, False]


def get_spells():
    attribute1_region = (500, 772, 700, 792)
    attribute2_region = (738, 772, 938, 792)
    attribute3_region = (976, 772, 1180, 792)

    attribute1_text = read_text_from_screen(attribute1_region)
    attribute2_text = read_text_from_screen(attribute2_region)
    attribute3_text = read_text_from_screen(attribute3_region)

    return attribute1_text, attribute2_text, attribute3_text


def draw_interface():
    start_button = font.render("Start/Stop - hotkey 'Q'", True, (200, 200, 200))
    title = title_font.render("Tvarinsky | Auto Gladiators Bot", True, (255, 255, 255))
    description_line1 = font.render(
        "Для корректной работы бота необходимо открыть Dota 2 в режиме",
        True,
        (220, 220, 220),
    )
    description_line2 = font.render(
        "полноэкранного окна (Windows) или оконного (Mac OS)", True, (220, 220, 220)
    )

    dota_status = "Dota 2 запущена" if dota_running else "Ожидание запуска Dota 2"
    dota_text = font.render(dota_status, True, WHITE)

    circle_color = (0, 255, 0) if running and dota_running else (255, 0, 0)
    pygame.draw.circle(screen, circle_color, (25, 205), 5)

    screen.blit(title, (25, 20))
    screen.blit(start_button, (35, 200))
    screen.blit(description_line1, (25, 50))
    screen.blit(description_line2, (25, 70))
    screen.blit(
        dota_text,
        (screen_width - dota_text.get_width() - 25, 200),
    )


def start_bot():
    global running
    running = True


def stop_bot():
    global running
    running = False


def toggle_bot():
    global running
    if dota_running:
        running = not running
        toggle_sound.play()


def on_press(key):
    try:
        if key.char == "q":
            toggle_bot()
    except AttributeError:
        pass


listener = Listener(on_press=on_press)
listener.start()


if __name__ == "__main__":
    pygame.display.set_caption("Tvarinsky | Auto Gladiators Bot")

    pygame.display.flip()

    while True:
        screen.fill((0, 0, 0))

        draw_interface()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        if dota_running and running:
            gold_region = (940, 1010, 1000, 1050)
            gold_text = read_text_from_screen(gold_region)

            gold_numbers = extract_numbers(gold_text)

            attribute_name = check_character_attributes()

            currentSpells = get_spells()

            if currentSpells and attribute_name:
                if attribute_name in attributes:
                    match_spells_with_attribute(
                        currentSpells, attribute_name, spells_bought_this_cycle
                    )
                else:
                    print("Attribute not found in attributes:", attribute_name)

        spells_bought_this_cycle = [False, False, False]

        dota_running = False
        for p in psutil.process_iter():
            try:
                if "Dota 2" in p.name() or "dota2" in p.name():
                    dota_running = True
                    break
            except psutil.NoSuchProcess:
                pass

        pygame.display.flip()
        time.sleep(0.1)
