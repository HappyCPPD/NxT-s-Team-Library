
### Description
- Challenge Name: LSD
- Challenge Description - Images are cool, trippy images are cooler. I sometimes wonder what the inspiration is for art like this.. hmm...? These days so many things happen in parallel, its hard to lose track fr..
- Challenge Files - `output.ppm` and `generator`

### Write-Up
The file `generator` is an `nvcc` compiled binary which is designed to run on Nvidia hardware that supports `cuda`.

We can extract the instructions (in `ptx`) from the file using the command `cuobjdump -ptx generator > disasm`. The output for this is in the `disasm` file provided.

In the dump, we can see the kernel function name 
`.visible .entry _Z16renderMandelbrotP6uchar3PiiS1_iidddddii(`
which is misleading, because the actual algorithm renders a `newton` fractal into `output.ppm`.

The challenge is compiled from the file in `main.cu`. It essentially takes the the following arguments
`./generator <flag_plaintext> <image_height> <image_width> <max_steps> <radius>`

Trying to dissect the file with IDA or Binary Ninja, you can find the logic that calls the CUDA kernel itself. Essentially it takes the `flag_plaintext` in `argv[1]` and puts it into a `std::vector<int>` with some encoding

```c++
 std::vector<int> polynomial;
 for (auto c : flag) {
 std::cerr << c << std::endl;
 if (c == '{') polynomial.push_back(38);
 else if (c == '}') polynomial.push_back(39);
 else if (c >= 'a') polynomial.push_back(c - 'a');
 else polynomial.push_back(c - '0' + 26);
 }
```

Then the kernel itself is called 
```c++
renderMandelbrot <<<grid_size, block_size>>>(
 d_outputImage, 
 d_polynomial, polydegree, 
 d_derivative, deridegree, 
 maxSteps, escapeRadius, 
 xmin, xmax, 
 ymin, ymax, 
 width, height
);
```

and the output is saved into an `output.ppm` file with `P6` format
Opening the output with GIMP we can see a fractal looking image, that in fact is a **Newton Fractal** that is generated using the inputted flag's ciphertext.

The flag's `ascii` characters are converted into the coefficients of a polynomial. Given a polynomial, we can generate a newton-fractal by considering a complex plane, and for each complex number finding the number of iterations it takes for it to converge into a root using the Newton-Raphson method. Which is what this kernel does.

```c++
int step = -1;
for (; step < maxSteps; step++) {
 cuDoubleComplex fz = evalPoly(polynomial, polydegree, z);
 cuDoubleComplex fdz = evalPoly(derivative, deridegree, z);

 if (cuCabs(fdz) < 1e-8) break;

 cuDoubleComplex stepsize = cuCdiv(fz, fdz);
 cuDoubleComplex zNext = cuCsub(z, stepsize);

 double dist = cuCabs(cuCsub(zNext, z));
 if (dist < 1.6e-7) break;

 if (cuCabs(zNext) > escapeRadius) {
 break;
 }
 z = zNext;
}
```

And it is colored using the following formula
```c++
uchar3 color;
if (step == maxSteps) color = {0, 0, 0};
else {
 float t = (float)step / (float)maxSteps;
 // printf("%f\n", t);
 color = float_to_uchar3(1 - t);
}
canvas[idy * width + idx] = color;
```

We notice that the color is white if the number of steps are 0. Essentially if the complex number is a `root` of the equation, then the pixel is colored white. 
We can use this to find the flag, as we can rewrite the polynomial as the product of `(z - root)`. Therefore finding the roots of the equation is enough. The size of the output image guarantees that all the roots are present in the image and full-white color.

We can now write a solver to solve for the flag itself from output.ppm, which I have provided as `solver.cpp`. Running the code we get.. 

```
shobwq@ShonLappy:~/CTFS/h4ckc0n/rev/lsd/all-files$ g++ solver.cpp -o solver2
shobwq@ShonLappy:~/CTFS/h4ckc0n/rev/lsd/all-files$ ./solver2
Width : 25600
Height: 14400
-0.885 -0.366
-0.885 0.366
-0.861 -0
-0.717 -0.829
-0.717 0.829
-0.106 -0
-0.068 -0.952
-0.068 0.952
0.313 -0.989
0.313 0.989
0.558 -0.706
0.558 0.706
0.912 -0.361
0.912 0.361
(0.0767965,0) (0.768919,-9.31323e-09) (0.435619,-1.78814e-07) (0.254771,1.01328e-06) (0.973072,-1.90735e-06) (0.40911,1.66893e-06) (0.356707,-1.66893e-06) (0.665178,9.53674e-07) (0.0756818,1.90735e-06) (-0.00464487,-2.6226e-06) (0.687462,7.15256e-07) (0.71502,8.34465e-07) (0.689627,-4.76837e-07) (0.741,0) (1,0)
39.0643
d4rk{qo0da1213}
```

`d4rk{qo0da1213}` is the flag for this challenge

