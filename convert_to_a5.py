#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для конвертации PDF файлов в формат A5 для печати
Масштабирует содержимое страниц, чтобы они поместились в формат A5 (148 x 210 мм)
"""

import os
import sys
import argparse
import fitz  # PyMuPDF
from PIL import Image
import io
from tqdm import tqdm

# Размеры A5 в миллиметрах
A5_WIDTH_MM = 148
A5_HEIGHT_MM = 210

# Конвертация мм в точки (1 мм = 2.83465 точек при 72 DPI)
MM_TO_POINTS = 2.83465

# Размеры A5 в точках
A5_WIDTH_PT = A5_WIDTH_MM * MM_TO_POINTS
A5_HEIGHT_PT = A5_HEIGHT_MM * MM_TO_POINTS

def convert_pdf_to_a5(input_path, output_path, fit_mode='fit', dpi=300):
    """
    Конвертирует PDF в формат A5 с высоким качеством
    
    Args:
        input_path: путь к входному PDF
        output_path: путь к выходному PDF
        fit_mode: режим подгонки ('fit' - вписать, 'fill' - заполнить, 'stretch' - растянуть)
        dpi: разрешение для рендеринга (по умолчанию 300 DPI для печати)
    """
    print(f"Конвертация файла: {os.path.basename(input_path)}")
    print(f"Целевой формат: A5 ({A5_WIDTH_MM} x {A5_HEIGHT_MM} мм)")
    print(f"Режим подгонки: {fit_mode}")
    print(f"Разрешение: {dpi} DPI")
    print()
    
    # Открываем PDF
    doc = fitz.open(input_path)
    total_pages = len(doc)
    
    print(f"Количество страниц: {total_pages}")
    print()
    
    # Создаем новый PDF
    new_doc = fitz.open()
    
    # Вычисляем zoom для заданного DPI (72 DPI = 1.0 zoom)
    zoom = dpi / 72.0
    
    for page_num in tqdm(range(total_pages), desc="Обработка страниц", ncols=80):
        page = doc[page_num]
        original_rect = page.rect
        original_width = original_rect.width
        original_height = original_rect.height
        
        # Вычисляем масштаб для подгонки в A5
        scale_x = A5_WIDTH_PT / original_width
        scale_y = A5_HEIGHT_PT / original_height
        
        if fit_mode == 'fit':
            # Вписать: используем минимальный масштаб, чтобы все поместилось
            scale = min(scale_x, scale_y)
        elif fit_mode == 'fill':
            # Заполнить: используем максимальный масштаб, чтобы заполнить весь формат
            scale = max(scale_x, scale_y)
        else:  # stretch
            # Растянуть: используем разные масштабы для X и Y
            scale = None
        
        # Вычисляем размеры для вставки в A5
        if scale is not None:
            # Единый масштаб для X и Y
            scaled_width = original_width * scale
            scaled_height = original_height * scale
            
            # Центрируем содержимое
            x_offset = (A5_WIDTH_PT - scaled_width) / 2
            y_offset = (A5_HEIGHT_PT - scaled_height) / 2
            
            target_width_pt = scaled_width
            target_height_pt = scaled_height
        else:
            # Разные масштабы для X и Y (растяжение)
            x_offset = 0
            y_offset = 0
            target_width_pt = A5_WIDTH_PT
            target_height_pt = A5_HEIGHT_PT
        
        # Рендерим страницу в изображение с высоким разрешением
        # Рендерим оригинальную страницу с высоким разрешением
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # Конвертируем в PIL Image для обработки
        img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Вычисляем размеры в пикселях для финального изображения
        # Нужно масштабировать от оригинального размера (в пикселях) до целевого размера (в пикселях)
        target_width_px = int(target_width_pt * zoom)
        target_height_px = int(target_height_pt * zoom)
        
        # Масштабируем изображение до финального размера с высоким качеством
        # Используем LANCZOS для лучшего качества масштабирования
        img_resized = img_pil.resize((target_width_px, target_height_px), Image.Resampling.LANCZOS)
        
        # Конвертируем обратно в байты с высоким качеством
        img_bytes_io = io.BytesIO()
        img_resized.save(img_bytes_io, format='PNG', compress_level=1)  # Минимальное сжатие для качества
        img_bytes = img_bytes_io.getvalue()
        
        # Создаем новую страницу A5
        new_page = new_doc.new_page(width=A5_WIDTH_PT, height=A5_HEIGHT_PT)
        
        # Вставляем изображение
        target_rect = fitz.Rect(
            x_offset,
            y_offset,
            x_offset + target_width_pt,
            y_offset + target_height_pt
        )
        new_page.insert_image(target_rect, stream=img_bytes)
    
    # Сохраняем результат
    print(f"\nСохранение результата в: {output_path}")
    new_doc.save(output_path)
    new_doc.close()
    doc.close()
    
    print(f"\n✓ Готово! Конвертировано страниц: {total_pages}")
    print(f"✓ Файл сохранен: {output_path}")
    print(f"✓ Размер страниц: A5 ({A5_WIDTH_MM} x {A5_HEIGHT_MM} мм)")

def main():
    parser = argparse.ArgumentParser(
        description='Конвертация PDF файлов в формат A5 для печати',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s input.pdf output.pdf
  %(prog)s input.pdf output.pdf --fit fill
  %(prog)s input.pdf output.pdf --fit stretch
  %(prog)s input.pdf output.pdf --dpi 300
  %(prog)s input.pdf output.pdf --dpi 600 --fit fill

Режимы подгонки:
  fit      - вписать содержимое в A5 (сохраняет пропорции, могут быть поля)
  fill     - заполнить весь формат A5 (сохраняет пропорции, может обрезаться)
  stretch  - растянуть содержимое на весь формат A5 (может исказить пропорции)

Качество:
  --dpi    - разрешение для рендеринга (по умолчанию: 300 DPI)
             Рекомендуется: 300 DPI для печати, 150-200 DPI для экрана
        """
    )
    
    parser.add_argument(
        'input',
        type=str,
        help='Путь к входному PDF файлу'
    )
    
    parser.add_argument(
        'output',
        type=str,
        help='Путь к выходному PDF файлу'
    )
    
    parser.add_argument(
        '--fit',
        type=str,
        choices=['fit', 'fill', 'stretch'],
        default='fit',
        help='Режим подгонки содержимого (по умолчанию: fit)'
    )
    
    parser.add_argument(
        '--dpi',
        type=int,
        default=300,
        help='Разрешение для рендеринга в DPI (по умолчанию: 300 для печати)'
    )
    
    args = parser.parse_args()
    
    # Проверяем существование входного файла
    if not os.path.exists(args.input):
        print(f"Ошибка: файл не найден: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # Проверяем, что входной файл - PDF
    if not args.input.lower().endswith('.pdf'):
        print(f"Ошибка: входной файл должен быть PDF: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # Проверяем, что выходной файл - PDF
    if not args.output.lower().endswith('.pdf'):
        print(f"Ошибка: выходной файл должен быть PDF: {args.output}", file=sys.stderr)
        sys.exit(1)
    
    # Проверяем DPI
    if args.dpi < 72:
        print(f"Предупреждение: DPI меньше 72 может привести к низкому качеству", file=sys.stderr)
    if args.dpi > 600:
        print(f"Предупреждение: DPI больше 600 может привести к очень большим файлам", file=sys.stderr)
    
    # Обрабатываем файл
    try:
        convert_pdf_to_a5(
            input_path=args.input,
            output_path=args.output,
            fit_mode=args.fit,
            dpi=args.dpi
        )
    except Exception as e:
        print(f"Ошибка при обработке: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

