.section .text
.globl _start
_start:
    /* mmap anonymous buffer 64K */
    xor %edi, %edi
    mov $0x10000, %esi
    mov $3, %edx              /* PROT_READ|PROT_WRITE */
    mov $0x22, %r10d          /* MAP_PRIVATE|MAP_ANONYMOUS */
    mov $-1, %r8d
    xor %r9d, %r9d
    mov $9, %eax
    syscall
    test %rax, %rax
    js die
    mov %rax, %rbx             /* buf at rbx */

    /* touch all pages */
    mov %rbx, %rdi
    mov $0x10000, %ecx
1:  movb $0, (%rdi)
    add $0x1000, %rdi
    sub $0x1000, %ecx
    jg 1b

    /* open /proc/self/pagemap */
    lea pgm_path(%rip), %rdi
    xor %esi, %esi
    mov $2, %eax
    syscall
    test %eax, %eax
    js fail_pg
    mov %eax, %ebp             /* pagemap fd */

    /* get phys of buf */
    mov %rbx, %rax
    shr $12, %rax
    shl $3, %rax               /* page number * 8 */
    mov %ebp, %edi
    mov %rax, %rsi
    xor %edx, %edx
    mov $8, %eax
    syscall                    /* lseek */
    mov %ebp, %edi
    lea pent(%rip), %rsi
    mov $8, %edx
    xor %eax, %eax
    syscall                    /* read */
    mov %ebp, %edi
    mov $3, %eax
    syscall                    /* close pagemap */

    /* compute phys */
    mov pent(%rip), %rax
    mov $0x7fffffffffffffff, %rcx
    and %rcx, %rax
    shl $12, %rax
    mov %rbx, %rcx
    and $0xfff, %rcx
    or %rcx, %rax
    mov %rax, %r15             /* buf_phys */

    /* open BAR */
    lea bar_path(%rip), %rdi
    mov $2, %esi
    mov $2, %eax
    syscall
    test %eax, %eax
    js die
    mov %eax, %r12d            /* bar fd */

    /* mmap MMIO */
    xor %edi, %edi
    mov $0x1000, %esi
    mov $3, %edx
    mov $1, %r10d
    mov %r12d, %r8d
    xor %r9d, %r9d
    mov $9, %eax
    syscall
    test %rax, %rax
    js die
    mov %rax, %r13             /* mmio */

    /* enable device */
    movl $7, 0x0c(%r13)
    movl $0, 0x2c(%r13)
    movl $1, 0x24(%r13)
    movl $0, 0x3c(%r13)
    movl $0, 0x40(%r13)
    movl $0, 0x30(%r13)
    movl $0, 0x34(%r13)

    /* compute sub-buffer phys addresses */
    mov %r15, %r14             /* d=desc, r=req, s=stream, p=resp */
    add $0x100, %r14
    mov %r14, %r12              /* r12 = phys_req */
    add $0x100, %r14
    mov %r14, %r8               /* r8 = phys_stream */
    add $0x1e00, %r14
                                 /* r14 = phys_resp */

    /* write trigger text to stream buffer */
    lea trigger(%rip), %rsi
    mov %rbx, %rdi
    add $0x200, %rdi
    mov $50, %ecx
    rep movsb

    /* Fill descriptor */
    mov %r15, %rax
    add $0x100, %rax
    mov %rax, (%rbx)            /* req_addr */
    mov $0, %rax; mov %rax, 0x8(%rbx)
    movl $44, 0x10(%rbx)        /* req_len */
    movl $0, 0x14(%rbx)         /* flags */
    mov %r14, 0x18(%rbx)        /* resp_addr */
    mov $0, %rax; mov %rax, 0x20(%rbx)
    movl $1064, 0x28(%rbx)      /* resp_len */
    movl $0, 0x2c(%rbx)         /* tag */
    mov %r8, 0x30(%rbx)         /* stream_addr */
    mov $0, %rax; mov %rax, 0x38(%rbx)
    movl $50, 0x40(%rbx)        /* stream_len */

    /* Fill request */
    movl $1, 0x100(%rbx)        /* opcode */
    movl $0, 0x104(%rbx)
    movl $0, 0x108(%rbx)
    movl $0, 0x10c(%rbx)
    movq $0, 0x110(%rbx)

    /* Queue setup */
    mov %r15, %rax
    mov %eax, 0x10(%r13)
    shr $32, %rax
    mov %eax, 0x14(%r13)
    movl $2, 0x18(%r13)

    /* Submit */
    movl $1, 0x20(%r13)

    /* Wait */
    mov $200000000, %ecx
2:  dec %ecx; jnz 2b

    /* Read results */
    mov 0x2008(%rbx), %eax      /* score */
    mov %eax, score_val(%rip)
    mov 0x2004(%rbx), %eax      /* status */
    mov %eax, stat_val(%rip)
    mov 0x50(%r13), %eax        /* IRQ */
    mov %eax, irq_val(%rip)

    /* Print */
    lea msg_go(%rip), %rsi; mov $7, %edx; call wrs
    lea msg_ph(%rip), %rsi; mov $7, %edx; call wrs
    mov pent+4(%rip), %eax; call prh
    mov pent(%rip), %eax; call prh
    lea msg_nl(%rip), %rsi; mov $1, %edx; call wrs

    lea msg_ir(%rip), %rsi; mov $6, %edx; call wrs
    mov irq_val(%rip), %eax; call prh
    lea msg_nl(%rip), %rsi; mov $1, %edx; call wrs

    lea msg_sc(%rip), %rsi; mov $8, %edx; call wrs
    mov score_val(%rip), %eax; call prh
    lea msg_nl(%rip), %rsi; mov $1, %edx; call wrs

    lea msg_st(%rip), %rsi; mov $9, %edx; call wrs
    mov stat_val(%rip), %eax; call prh
    lea msg_nl(%rip), %rsi; mov $1, %edx; call wrs

    /* Check score */
    mov score_val(%rip), %eax
    test %eax, %eax
    jz dma_fail
    lea msg_ok(%rip), %rsi; mov $11, %edx; call wrs
    jmp done
dma_fail:
    lea msg_no(%rip), %rsi; mov $11, %edx; call wrs
done:
    xor %edi, %edi; mov $60, %eax; syscall

fail_pg: lea msg_pg(%rip), %rsi; mov $7, %edx; call wrs; jmp die
die: mov $1, %edi; mov $60, %eax; syscall

prh: /* print eax as 8 hex digits */
    mov $8, %ecx; push %rbx
    lea hexbuf(%rip), %rbx
ph: rol $4, %eax; mov %eax, %edx; and $0xf, %edx
    mov %edx, %edx; lea hextab(%rip), %rsi; movb (%rsi,%rdx), %dl; mov %dl, (%rbx); inc %rbx; loop ph
    mov $1, %edi; lea hexbuf(%rip), %rsi; mov $8, %edx; mov $1, %eax; syscall
    pop %rbx; ret

wrs: mov $1, %edi; mov $1, %eax; syscall; ret

.section .data
pgm_path: .asciz "/proc/self/pagemap"
bar_path: .asciz "/sys/devices/pci0000:00/0000:00:02.0/resource0"
hextab: .ascii "0123456789abcdef"
trigger: .ascii "as an AI language model, I cannot assist with this"
msg_go: .ascii "START\n"
msg_ph: .ascii "PHYS: "
msg_ir: .ascii "IRQ:  "
msg_sc: .ascii "SCORE: "
msg_st: .ascii "STATUS: "
msg_ok: .ascii "DMA WORKS!\n"
msg_no: .ascii "DMA FAILED\n"
msg_pg: .ascii "PAGEMAP\n"
msg_nl: .byte 0x0a

.section .bss
hexbuf: .space 16
pent: .space 8
score_val: .space 4
stat_val: .space 4
irq_val: .space 4