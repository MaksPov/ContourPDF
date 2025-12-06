#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для анализа PDF файлов с развертками и цветными фигурами
"""

import sys
import os

def analyze_pdf_with_pymupdf(pdf_path):
    """Анализ PDF с использованием PyMuPDF"""
    try:
        import fitz  # PyMuPDF
        print(f"\n{'='*60}")
        print(f"Анализ файла: {os.path.basename(pdf_path)}")
        print(f"{'='*60}")
        
        doc = fitz.open(pdf_path)
        print(f"Количество страниц: {len(doc)}")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            print(f"\n--- Страница {page_num + 1} ---")
            
            # Получаем размеры страницы
            rect = page.rect
            print(f"Размеры страницы: {rect.width:.2f} x {rect.height:.2f} точек")
            
            # Извлекаем изображения
            image_list = page.get_images()
            print(f"Количество изображений: {len(image_list)}")
            
            # Анализируем векторные объекты (пути, линии, фигуры)
            drawings = page.get_drawings()
            print(f"Количество векторных объектов: {len(drawings)}")
            
            # Анализируем цвета в векторных объектах
            colors_found = set()
            for drawing in drawings:
                # Анализируем заливку
                if 'fill' in drawing:
                    fill_color = drawing['fill']
                    if fill_color:
                        colors_found.add(tuple(fill_color[:3]) if len(fill_color) >= 3 else tuple(fill_color))
                
                # Анализируем обводку
                if 'color' in drawing:
                    stroke_color = drawing['color']
                    if stroke_color:
                        colors_found.add(tuple(stroke_color[:3]) if len(stroke_color) >= 3 else tuple(stroke_color))
            
            if colors_found:
                print(f"Найдено уникальных цветов в векторных объектах: {len(colors_found)}")
                for i, color in enumerate(colors_found, 1):
                    if len(color) == 3:
                        print(f"  Цвет {i}: RGB({color[0]:.3f}, {color[1]:.3f}, {color[2]:.3f})")
            
            # Получаем текст (если есть)
            text = page.get_text()
            if text.strip():
                print(f"Текст на странице: {len(text)} символов")
            else:
                print("Текст на странице: отсутствует")
        
        doc.close()
        return True
        
    except ImportError:
        print("PyMuPDF не установлен. Пробую другой метод...")
        return False
    except Exception as e:
        print(f"Ошибка при анализе с PyMuPDF: {e}")
        return False

def analyze_pdf_with_pdfplumber(pdf_path):
    """Анализ PDF с использованием pdfplumber"""
    try:
        import pdfplumber
        print(f"\n{'='*60}")
        print(f"Анализ файла: {os.path.basename(pdf_path)}")
        print(f"{'='*60}")
        
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Количество страниц: {len(pdf.pages)}")
            
            for page_num, page in enumerate(pdf.pages):
                print(f"\n--- Страница {page_num + 1} ---")
                print(f"Размеры страницы: {page.width:.2f} x {page.height:.2f} точек")
                
                # Извлекаем изображения
                images = page.images
                print(f"Количество изображений: {len(images)}")
                for i, img in enumerate(images, 1):
                    print(f"  Изображение {i}: {img['width']:.1f} x {img['height']:.1f} точек")
                
                # Извлекаем векторные объекты
                paths = page.paths
                print(f"Количество путей (paths): {len(paths)}")
                
                # Извлекаем линии
                lines = page.lines
                print(f"Количество линий: {len(lines)}")
                
                # Извлекаем прямоугольники
                rects = page.rects
                print(f"Количество прямоугольников: {len(rects)}")
                
                # Извлекаем кривые
                curves = page.curves
                print(f"Количество кривых: {len(curves)}")
        
        return True
        
    except ImportError:
        print("pdfplumber не установлен.")
        return False
    except Exception as e:
        print(f"Ошибка при анализе с pdfplumber: {e}")
        return False

def main():
    # Находим все PDF файлы в текущей директории
    pdf_files = [
        "Лисичка без текста и контуров.pdf",
        "Лисичка_тест_стр1.pdf"
    ]
    
    # Получаем абсолютный путь к директории
    base_dir = "/home/maskpov/Рабочий стол/app"
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(base_dir, pdf_file)
        if os.path.exists(pdf_path):
            # Пробуем разные методы анализа
            if not analyze_pdf_with_pymupdf(pdf_path):
                analyze_pdf_with_pdfplumber(pdf_path)
        else:
            print(f"Файл не найден: {pdf_path}")

if __name__ == "__main__":
    main()

