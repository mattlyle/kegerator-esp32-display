#!/usr/bin/env python3
"""
Draws the display's artwork into images/: the keg (empty and full, for the level) and the
background texture the display uses. Everything is drawn from code so it can be tweaked and
redrawn, rather than being a binary nobody can edit.

    .venv/bin/python tools/make_art.py

To try the other backgrounds, this draws all of them into images/options/ (not committed):

    .venv/bin/python tools/make_art.py --all

The keg is drawn 4 times bigger than it's shown and scaled down, which smooths its edges.
"""

import argparse
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "images"
OPTIONS_OUT = OUT / "options"

# the background the display uses, one of TEXTURES below
USED_TEXTURE = "bubbles"

SCREEN_W = 320
SCREEN_H = 480

# shown size of the keg on a tap card, and how much bigger it's drawn
KEG_W = 52
KEG_H = 96
SCALE = 4

BEER_TOP = (246, 186, 82)
BEER_BOTTOM = (176, 104, 26)

########################################################################################################################
# the keg


def SteelColor( t ):
    """The color across a stainless cylinder, t from 0 (left edge) to 1 (right edge): dark at the
    edges, a bright highlight a third of the way in, a softer second one near the right."""
    base = 70 + 95 * math.sin( math.pi * t ) ** 0.8
    highlight = 90 * math.exp( -( ( t - 0.32 ) / 0.07 ) ** 2 )
    second = 35 * math.exp( -( ( t - 0.78 ) / 0.05 ) ** 2 )
    v = min( 255, base + highlight + second )
    return ( int( v * 0.94 ), int( v * 0.97 ), int( v ) )


def KegShape( w, h ):
    """The keg's outline as a mask: a top chime with two hand holes, the body with two rolling
    bands, and a bottom chime. Returns ( mask, body mask, band list )."""
    mask = Image.new( "L", ( w, h ), 0 )
    body = Image.new( "L", ( w, h ), 0 )
    draw = ImageDraw.Draw( mask )
    body_draw = ImageDraw.Draw( body )

    chime_inset = w * 0.08
    body_inset = w * 0.04
    chime_top_h = h * 0.15
    chime_bottom_h = h * 0.07

    # top chime, with its two hand holes cut out below
    draw.rounded_rectangle( [ chime_inset, 0, w - chime_inset, chime_top_h ], radius = w * 0.05,
                            fill = 255 )
    # body: a straight cylinder with a rounded shoulder and foot
    body_box = [ body_inset, chime_top_h * 0.8, w - body_inset, h - chime_bottom_h * 0.6 ]
    draw.rounded_rectangle( body_box, radius = w * 0.12, fill = 255 )
    body_draw.rounded_rectangle( body_box, radius = w * 0.12, fill = 255 )
    # bottom chime
    draw.rounded_rectangle( [ chime_inset, h - chime_bottom_h, w - chime_inset, h ],
                            radius = w * 0.04, fill = 255 )

    # the rolling bands bulge out a little past the body
    bands = []
    for frac in ( 0.38, 0.72 ):
        y = h * frac
        band = [ 0, y - h * 0.022, w, y + h * 0.022 ]
        draw.rounded_rectangle( band, radius = h * 0.02, fill = 255 )
        bands.append( band )

    # hand holes through the top chime
    hole_h = chime_top_h * 0.38
    hole_y = chime_top_h * 0.22
    for left in ( w * 0.22, w * 0.56 ):
        draw.rounded_rectangle( [ left, hole_y, left + w * 0.22, hole_y + hole_h ],
                                radius = hole_h / 2, fill = 0 )

    return mask, body, bands


def DrawKeg( full ):
    w = KEG_W * SCALE
    h = KEG_H * SCALE
    mask, body, bands = KegShape( w, h )

    # stainless shading, the same down every column
    steel = Image.new( "RGB", ( w, h ) )
    for x in range( w ):
        color = SteelColor( x / ( w - 1 ) )
        for y in range( h ):
            steel.putpixel( ( x, y ), color )

    art = steel
    if full:
        # the body takes the beer's color, keeping the steel's highlights so it still reads as a
        # rounded keg
        beer = Image.new( "RGB", ( w, h ) )
        for y in range( h ):
            t = y / ( h - 1 )
            color = tuple( int( BEER_TOP[ i ] + ( BEER_BOTTOM[ i ] - BEER_TOP[ i ] ) * t )
                           for i in range( 3 ) )
            for x in range( w ):
                beer.putpixel( ( x, y ), color )
        tinted = ImageChops.multiply( beer, steel.point( lambda v: min( 255, v + 70 ) ) )
        art = Image.composite( tinted, steel, body )
    else:
        # an empty keg is the plain steel, a little darker so the full part stands out against it
        art = steel.point( lambda v: int( v * 0.55 ) )

    # dark seams where the bands and chimes meet the body
    draw = ImageDraw.Draw( art )
    for band in bands:
        draw.line( [ band[ 0 ], band[ 1 ], band[ 2 ], band[ 1 ] ], fill = ( 20, 22, 25 ),
                   width = SCALE )
        draw.line( [ band[ 0 ], band[ 3 ], band[ 2 ], band[ 3 ] ], fill = ( 20, 22, 25 ),
                   width = SCALE )

    rgba = art.convert( "RGBA" )
    rgba.putalpha( mask )
    return rgba.resize( ( KEG_W, KEG_H ), Image.LANCZOS )


########################################################################################################################
# textures


def Noise( w, h, cells_x, cells_y, seed ):
    """Smooth value noise: random values on a coarse grid, scaled up smoothly."""
    rng = random.Random( seed )
    small = Image.new( "L", ( cells_x, cells_y ) )
    small.putdata( [ rng.randint( 0, 255 ) for _ in range( cells_x * cells_y ) ] )
    return small.resize( ( w, h ), Image.BICUBIC )


def Grain( w, h, seed, amount ):
    rng = random.Random( seed )
    img = Image.new( "L", ( w, h ) )
    img.putdata( [ 128 + rng.randint( -amount, amount ) for _ in range( w * h ) ] )
    return img


def Colorize( gray, dark, light ):
    """Maps a grayscale image onto a color ramp from dark to light."""
    lut = []
    for i in range( 3 ):
        lut += [ int( dark[ i ] + ( light[ i ] - dark[ i ] ) * v / 255 ) for v in range( 256 ) ]
    return gray.convert( "RGB" ).point( lut )


def Blend( a, b, amount ):
    return Image.blend( a, b, amount )


def BrushedSteel():
    w, h = SCREEN_W, SCREEN_H
    # long horizontal streaks: noise with lots of rows but few columns, stretched sideways
    streaks = Noise( w, h, 6, h, 1 )
    fine = Noise( w, h, 40, h, 2 )
    gray = Blend( streaks, fine, 0.5 )
    gray = ImageChops.add( gray, Grain( w, h, 3, 10 ), scale = 1.0, offset = -128 )
    return Colorize( gray, ( 22, 24, 27 ), ( 62, 66, 71 ) )


def DarkWood():
    w, h = SCREEN_W, SCREEN_H
    rng = random.Random( 4 )
    img = Image.new( "RGB", ( w, h ) )
    plank_h = 60
    for top in range( 0, h, plank_h ):
        # grain: wavy horizontal lines, each plank its own pattern and tone
        grain = Image.new( "L", ( w, plank_h ) )
        phase = rng.random() * 10
        freq = 0.18 + rng.random() * 0.08
        wobble = Noise( w, plank_h, 5, 3, rng.randint( 0, 999 ) )
        pixels = []
        for y in range( plank_h ):
            for x in range( w ):
                bend = ( wobble.getpixel( ( x, y ) ) - 128 ) / 128 * 4
                v = math.sin( ( y + bend ) * freq * 3 + phase ) * 0.5 + 0.5
                pixels.append( int( 90 + 120 * v ** 3 ) )
        grain.putdata( pixels )
        grain = ImageChops.add( grain, Grain( w, plank_h, rng.randint( 0, 999 ), 12 ), offset = -128 )
        tone = 0.85 + rng.random() * 0.3
        plank = Colorize( grain, ( int( 30 * tone ), int( 18 * tone ), int( 11 * tone ) ),
                          ( int( 92 * tone ), int( 58 * tone ), int( 34 * tone ) ) )
        img.paste( plank, ( 0, top ) )
        # the dark seam between planks
        ImageDraw.Draw( img ).line( [ 0, top, w, top ], fill = ( 10, 6, 4 ), width = 2 )
    return img


def Chalkboard():
    w, h = SCREEN_W, SCREEN_H
    clouds = Noise( w, h, 8, 12, 5 ).filter( ImageFilter.GaussianBlur( 12 ) )
    wisps = Noise( w, h, 30, 45, 6 ).filter( ImageFilter.GaussianBlur( 3 ) )
    gray = Blend( clouds, wisps, 0.3 )
    gray = ImageChops.add( gray, Grain( w, h, 7, 14 ), offset = -128 )
    return Colorize( gray, ( 18, 26, 23 ), ( 52, 64, 58 ) )


def Slate():
    w, h = SCREEN_W, SCREEN_H
    big = Noise( w, h, 10, 15, 8 ).filter( ImageFilter.GaussianBlur( 6 ) )
    small = Noise( w, h, 80, 120, 9 )
    gray = Blend( big, small, 0.35 )
    gray = ImageChops.add( gray, Grain( w, h, 10, 16 ), offset = -128 )
    return Colorize( gray, ( 16, 18, 22 ), ( 58, 62, 70 ) )


def BrushedCopper():
    """Like the brushed steel, but in brewhouse copper."""
    w, h = SCREEN_W, SCREEN_H
    streaks = Noise( w, h, 6, h, 11 )
    fine = Noise( w, h, 40, h, 12 )
    gray = Blend( streaks, fine, 0.5 )
    gray = ImageChops.add( gray, Grain( w, h, 13, 10 ), scale = 1.0, offset = -128 )
    return Colorize( gray, ( 38, 18, 10 ), ( 112, 58, 32 ) )


def DiamondPlate():
    """Industrial tread plate: raised diagonal ribs on dark steel, in alternating directions."""
    w, h = SCREEN_W, SCREEN_H
    img = Colorize( ImageChops.add( Noise( w, h, 8, 12, 14 ), Grain( w, h, 15, 8 ), offset = -128 ),
                    ( 26, 28, 31 ), ( 48, 51, 56 ) )
    draw = ImageDraw.Draw( img )
    step = 22
    for row, cy in enumerate( range( -step, h + step, step ) ):
        for col, cx in enumerate( range( -step, w + step, step ) ):
            x = cx + ( step // 2 if row % 2 else 0 )
            # each rib is a short slanted bar; neighbours lean the other way
            lean = 1 if ( row + col ) % 2 else -1
            dx, dy = 6 * lean, -6
            # shadow under, the rib, then a highlight along its top edge
            draw.line( [ x - dx + 1, cy - dy + 1, x + dx + 1, cy + dy + 1 ], fill = ( 12, 13, 15 ), width = 5 )
            draw.line( [ x - dx, cy - dy, x + dx, cy + dy ], fill = ( 70, 74, 80 ), width = 4 )
            draw.line( [ x - dx - 1, cy - dy - 1, x + dx - 1, cy + dy - 1 ], fill = ( 112, 117, 124 ), width = 1 )
    return img


def CarbonFiber():
    """A 2x2 twill weave: little tiles shaded across or down, stepping one tile per row."""
    w, h = SCREEN_W, SCREEN_H
    tile = 6
    img = Image.new( "RGB", ( w, h ) )
    for ty in range( 0, h, tile ):
        for tx in range( 0, w, tile ):
            across = ( ( tx // tile ) + ( ty // tile ) ) % 4 < 2
            for y in range( tile ):
                for x in range( tile ):
                    t = ( y if across else x ) / ( tile - 1 )
                    v = int( 20 + 30 * math.sin( math.pi * t ) )
                    if tx + x < w and ty + y < h:
                        img.putpixel( ( tx + x, ty + y ), ( v, v, v + 3 ) )
    return img


def Bubbles():
    """Looking into a dark beer: deep amber fading to black, with rising carbonation bubbles."""
    w, h = SCREEN_W, SCREEN_H
    img = Image.new( "RGB", ( w, h ) )
    for y in range( h ):
        t = y / ( h - 1 )
        color = ( int( 60 - 48 * t ), int( 34 - 28 * t ), int( 10 - 7 * t ) )
        ImageDraw.Draw( img ).line( [ 0, y, w, y ], fill = color )
    glow = Noise( w, h, 4, 6, 16 ).filter( ImageFilter.GaussianBlur( 20 ) )
    img = Image.blend( img, Colorize( glow, ( 10, 5, 2 ), ( 70, 40, 12 ) ), 0.35 )
    draw = ImageDraw.Draw( img )
    rng = random.Random( 17 )
    # a few columns of bubbles, plus some loose ones
    columns = [ rng.randint( 10, w - 10 ) for _ in range( 7 ) ]
    for _ in range( 260 ):
        if rng.random() < 0.6:
            x = rng.choice( columns ) + rng.randint( -4, 4 )
        else:
            x = rng.randint( 0, w )
        y = rng.randint( 0, h )
        r = rng.choice( [ 1, 1, 1, 2, 2, 3 ] )
        draw.ellipse( [ x - r, y - r, x + r, y + r ], outline = ( 160, 110, 50 ) )
        draw.point( ( x - r // 2, y - r // 2 ), fill = ( 230, 190, 120 ) )
    return img


def Hops():
    """A scattered pattern of hop cones, faint on dark green."""
    w, h = SCREEN_W, SCREEN_H
    base = ImageChops.add( Noise( w, h, 6, 9, 18 ).filter( ImageFilter.GaussianBlur( 10 ) ),
                           Grain( w, h, 19, 8 ), offset = -128 )
    img = Colorize( base, ( 14, 22, 15 ), ( 30, 44, 30 ) )
    rng = random.Random( 20 )
    for row, cy in enumerate( range( 10, h + 40, 64 ) ):
        for cx in range( 10 + ( 32 if row % 2 else 0 ), w + 40, 64 ):
            cone = Image.new( "RGBA", ( 40, 56 ), ( 0, 0, 0, 0 ) )
            draw = ImageDraw.Draw( cone )
            # overlapping bracts, from the wide middle tapering to the tip, with a stem
            draw.line( [ 20, 0, 20, 8 ], fill = ( 70, 100, 60, 255 ), width = 2 )
            for i, ( y, half ) in enumerate( [ ( 10, 8 ), ( 16, 12 ), ( 23, 14 ), ( 30, 13 ),
                                               ( 37, 11 ), ( 43, 7 ) ] ):
                for x in ( 20 - half // 2, 20 + half // 2 ) if i % 2 else ( 20, ):
                    draw.ellipse( [ x - half // 2 - 2, y - 2, x + half // 2 + 2, y + 9 ],
                                  fill = ( 58, 86, 48, 255 ), outline = ( 92, 128, 74, 255 ) )
            cone = cone.rotate( rng.randint( -35, 35 ), resample = Image.BICUBIC, expand = True )
            img.paste( cone, ( cx - cone.width // 2, cy - cone.height // 2 ), cone )
    return img


def Honeycomb():
    """A honeycomb of hexagons, edges just lighter than the dark fill."""
    w, h = SCREEN_W, SCREEN_H
    img = Colorize( ImageChops.add( Noise( w, h, 6, 9, 21 ), Grain( w, h, 22, 6 ), offset = -128 ),
                    ( 18, 19, 22 ), ( 34, 36, 40 ) )
    draw = ImageDraw.Draw( img )
    r = 14
    hex_w = math.sqrt( 3 ) * r
    for row in range( int( h / ( 1.5 * r ) ) + 2 ):
        for col in range( int( w / hex_w ) + 2 ):
            cx = col * hex_w + ( hex_w / 2 if row % 2 else 0 )
            cy = row * 1.5 * r
            points = [ ( cx + r * math.cos( math.radians( 60 * k + 30 ) ),
                         cy + r * math.sin( math.radians( 60 * k + 30 ) ) ) for k in range( 6 ) ]
            draw.polygon( points, outline = ( 58, 62, 68 ) )
    return img


TEXTURES = {
    "steel": BrushedSteel,
    "wood": DarkWood,
    "chalk": Chalkboard,
    "slate": Slate,
    "copper": BrushedCopper,
    "diamond": DiamondPlate,
    "carbon": CarbonFiber,
    "bubbles": Bubbles,
    "hops": Hops,
    "honeycomb": Honeycomb,
    }

########################################################################################################################


def Main():
    parser = argparse.ArgumentParser( description = __doc__,
                                      formatter_class = argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--all", action = "store_true",
                         help = f"also draw every background into {OPTIONS_OUT}" )
    args = parser.parse_args()

    OUT.mkdir( exist_ok = True )
    DrawKeg( full = False ).save( OUT / "keg_empty.png" )
    DrawKeg( full = True ).save( OUT / "keg_full.png" )
    TEXTURES[ USED_TEXTURE ]().save( OUT / f"texture_{USED_TEXTURE}.png" )
    print( f"wrote the keg and the {USED_TEXTURE} background to {OUT}" )

    if args.all:
        OPTIONS_OUT.mkdir( exist_ok = True )
        for name, make in TEXTURES.items():
            make().save( OPTIONS_OUT / f"texture_{name}.png" )
        print( f"wrote all {len( TEXTURES )} backgrounds to {OPTIONS_OUT}" )


if __name__ == "__main__":
    Main()
