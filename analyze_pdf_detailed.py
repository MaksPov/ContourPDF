#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Детальный анализ PDF файлов с развертками и цветными фигурами
"""

import sys
import os
from collections import Counter

def analyze_pdf_detailed(pdf_path):
    """Детальный анализ PDF с извлечением цветов из изображений"""
    try:
        import fitz  # PyMuPDF
        from PIL import Image
        import io
        
        print(f"\n{'='*70}")
        print(f"ДЕТАЛЬНЫЙ АНАЛИЗ: {os.path.basename(pdf_path)}")
        print(f"{'='*70}")
        
        doc = fitz.open(pdf_path)
        print(f"Количество страниц: {len(doc)}\n")
        
        all_colors = []
        total_images = 0
        total_vector_objects = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            print(f"{'─'*70}")
            print(f"СТРАНИЦА {page_num + 1}")
            print(f"{'─'*70}")
            
            # Размеры страницы
            rect = page.rect
            print(f"Размеры: {rect.width:.1f} x {rect.height:.1f} точек (A4 формат)")
            
            # Анализ изображений
            image_list = page.get_images()
            print(f"\n📷 ИЗОБРАЖЕНИЯ: {len(image_list)}")
            
            page_colors = []
            for img_idx, img in enumerate(image_list, 1):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Открываем изображение для анализа цветов
                try:
                    img_pil = Image.open(io.BytesIO(image_bytes))
                    width, height = img_pil.size
                    print(f"  Изображение {img_idx}: {width}x{height} пикселей, формат: {image_ext}")
                    
                    # Анализируем цвета в изображении
                    if img_pil.mode in ('RGB', 'RGBA'):
                        # Получаем уникальные цвета (упрощенный метод - берем каждый 10-й пиксель)
                        colors = []
                        pixels = list(img_pil.getdata())
                        step = max(1, len(pixels) // 10000)  # Берем до 10000 пикселей для анализа
                        
                        for i in range(0, len(pixels), step):
                            pixel = pixels[i]
                            if isinstance(pixel, tuple):
                                if len(pixel) >= 3:
                                    colors.append(pixel[:3])
                        
                        if colors:
                            unique_colors = set(colors)
                            page_colors.extend(unique_colors)
                            print(f"    Уникальных цветов: {len(unique_colors)}")
                            
                            # Показываем топ-5 самых частых цветов
                            color_counter = Counter(colors)
                            top_colors = color_counter.most_common(5)
                            print(f"    Топ цветов:")
                            for color, count in top_colors:
                                r, g, b = color[:3]
                                print(f"      RGB({r:3d}, {g:3d}, {b:3d}) - встречается {count} раз")
                    
                except Exception as e:
                    print(f"    Ошибка при анализе изображения {img_idx}: {e}")
            
            total_images += len(image_list)
            all_colors.extend(page_colors)
            
            # Анализ векторных объектов
            drawings = page.get_drawings()
            print(f"\n✏️  ВЕКТОРНЫЕ ОБЪЕКТЫ: {len(drawings)}")
            total_vector_objects += len(drawings)
            
            vector_colors = set()
            for drawing in drawings:
                if 'fill' in drawing and drawing['fill']:
                    fill = drawing['fill']
                    if len(fill) >= 3:
                        vector_colors.add(tuple(fill[:3]))
                if 'color' in drawing and drawing['color']:
                    stroke = drawing['color']
                    if len(stroke) >= 3:
                        vector_colors.add(tuple(stroke[:3]))
            
            if vector_colors:
                print(f"  Уникальных цветов в векторах: {len(vector_colors)}")
                for color in vector_colors:
                    r, g, b = [int(c * 255) if c <= 1 else int(c) for c in color[:3]]
                    print(f"    RGB({r:3d}, {g:3d}, {b:3d})")
            
            # Текст
            text = page.get_text().strip()
            if text:
                print(f"\n📝 ТЕКСТ: {len(text)} символов")
                print(f"  Превью: {text[:50]}...")
            else:
                print(f"\n📝 ТЕКСТ: отсутствует")
            
            print()
        
        # Общая статистика
        print(f"{'='*70}")
        print("ОБЩАЯ СТАТИСТИКА")
        print(f"{'='*70}")
        print(f"Всего страниц: {len(doc)}")
        print(f"Всего изображений: {total_images}")
        print(f"Всего векторных объектов: {total_vector_objects}")
        
        if all_colors:
            unique_all_colors = set(all_colors)
            print(f"\n🎨 УНИКАЛЬНЫХ ЦВЕТОВ В ИЗОБРАЖЕНИЯХ: {len(unique_all_colors)}")
            
            # Группируем похожие цвета (с допуском)
            def color_distance(c1, c2):
                return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5
            
            color_groups = []
            for color in unique_all_colors:
                added = False
                for group in color_groups:
                    if color_distance(color, group[0]) < 30:  # Порог схожести
                        group.append(color)
                        added = True
                        break
                if not added:
                    color_groups.append([color])
            
            print(f"Групп похожих цветов: {len(color_groups)}")
            print("\nОсновные цветовые группы:")
            for i, group in enumerate(sorted(color_groups, key=len, reverse=True)[:10], 1):
                avg_color = tuple(int(sum(c[j] for c in group) / len(group)) for j in range(3))
                r, g, b = avg_color
                print(f"  Группа {i}: RGB({r:3d}, {g:3d}, {b:3d}) - {len(group)} вариантов")
        
        doc.close()
        
    except ImportError as e:
        print(f"Не установлена необходимая библиотека: {e}")
        print("Установите: pip install PyMuPDF Pillow")
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

def main():
    pdf_files = [
        "Лисичка без текста и контуров.pdf",
        "Лисичка_тест_стр1.pdf"
    ]
    
    base_dir = "/home/maskpov/Рабочий стол/app"
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(base_dir, pdf_file)
        if os.path.exists(pdf_path):
            analyze_pdf_detailed(pdf_path)
        else:
            print(f"Файл не найден: {pdf_path}")

if __name__ == "__main__":
    main()

