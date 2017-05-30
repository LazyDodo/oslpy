# OSLPY

OSLPY is a blender addon that converts OSL code to nodegroups.

How to install
--------------------------

1. Blender 2.78 is a minimum required version.
2. [Download][addon] the add-on.
3. Go to Blender 'User Preferences' -> 'Add-ons' category.
4. Use 'Install from File...' to install add-on from downloaded zip archive.

Note for mac users:

* Safari browser will automatically unpack downloaded zip archive, so in order to install the add-on, you have to pack folder with add-on files back into zip archive. Or use a different browser to download add-on.

## Why?

OSL is highly flexible but comes with one rather large downside, it doesn't run on the GPU and even when rendered on the CPU it tends to be slower than rending without OSL. This addon converts a subset of OSL that can be expressed in nodegroups in cycles to nodegroups that can run on the GPU (even when redered on the cpu they are faster than the original osl script at times, results may vary though)

## Can I just use any OSL script and expect it to work?

Sadly: no. 

This add-on only converts the bits of OSL that can be expressed in cycles nodes. So if it wasn't possible in the past it won't be possible now, so...

- OSL's wide range of noise sources: unsupported
- while loops: unsupported
- closures: unsupported
- string functions: unsupported
- raytracing functions: unsupported
- Returning from the middle of a function: unsupported

## This doesn't sound overly useful, what is it good for?! what does work?!

- Most purely procedural shaders will work or can be made to work with minimal changes, there are a bunch of example scripts in the examples folder
- most math based functions like sin/cos/tan/asin/acos/atan/atan2/dot/length/add/subtract/multiply/ceil/floor/mod etc
- Limited support for static loops, loops in the from ```for (i=0; i<10; i++) { do something }``` will automatically be unrolled at compile time. 
- if constructs (like ```if (x) y=a; else y=b;``` )
- most logical operations and/or/xor (like ```if (x and not y) y=a; else y=b;``` )
- function calls
- Limited static array access

## Why would I want to use it?

-It is easier to develop and maintain code than it is to develop and maintain a large nodegroup.

## There's bugs
Yeah those happen, if you think you found one, open up an issue with an as small as possible repro case and i'll be happy to take a look for you.

## Known issues

### Material view doesn't work
This is a blender issue, not something that oslpy can fix sadly. 
 
## Work arounds.

### No support for returning in the middle of a function.

The following function will cause issues for oslpy (code taken from [chainmail] script)

```
float rmap(float a, float b, float ra[3] )
{
    if ( between(ra[0], a, b) ) { return ra[0]; }
    if ( between(ra[1], a, b) ) { return ra[1]; }
    if ( between(ra[2], a, b) ) { return ra[2]; }
    return -1;
}
```
Given cycles doesn't support any jump instructions, this bit of code is problematic to translate. however with some manual changes, it can be made to work.

```
float rmap(float a, float b, float ra[3] )
{
    float result = -1;
    if ( between(ra[0], a, b) )
        result = ra[0]; 
    else if ( between(ra[1], a, b) ) 
        result = ra[1];
    else if ( between(ra[2], a, b) )
        result = ra[2]; 
    return result;
}
```


[chainmail]: https://github.com/sambler/osl-shaders/blob/master/patterns/MAChainmail/MAChainmail.osl
[addon]: https://github.com/LazyDodo/oslpy/archive/master.zip
