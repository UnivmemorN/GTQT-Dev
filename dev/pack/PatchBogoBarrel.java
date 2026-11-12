import java.nio.file.Files;
import java.nio.file.Path;
import org.objectweb.asm.*;

/** Gate the optional Future MC barrel integration on its class resource as well as its mod id. */
public final class PatchBogoBarrel implements Opcodes {
    public static void main(String[] args) throws Exception {
        ClassReader input = new ClassReader(Files.readAllBytes(Path.of(args[0])));
        ClassWriter output = new ClassWriter(input, ClassWriter.COMPUTE_MAXS);
        int[] changes = {0};
        input.accept(new ClassVisitor(ASM9, output) {
            @Override
            public MethodVisitor visitMethod(int access, String name, String desc, String sig, String[] exceptions) {
                MethodVisitor method = super.visitMethod(access, name, desc, sig, exceptions);
                if (!name.equals("init") || !desc.equals("(Lcom/cleanroommc/bogosorter/api/IBogoSortAPI;)V")) return method;
                return new MethodVisitor(ASM9, method) {
                    boolean futureId;
                    boolean futureLoaded;

                    @Override
                    public void visitLdcInsn(Object value) {
                        futureId = "futuremc".equals(value);
                        super.visitLdcInsn(value);
                    }

                    @Override
                    public void visitMethodInsn(int opcode, String owner, String name, String desc, boolean itf) {
                        futureLoaded = futureId && opcode == INVOKESTATIC && owner.equals("net/minecraftforge/fml/common/Loader")
                                && name.equals("isModLoaded") && desc.equals("(Ljava/lang/String;)Z");
                        futureId = false;
                        super.visitMethodInsn(opcode, owner, name, desc, itf);
                    }

                    @Override
                    public void visitJumpInsn(int opcode, Label target) {
                        super.visitJumpInsn(opcode, target);
                        if (futureLoaded && opcode == IFEQ) {
                            super.visitLdcInsn(Type.getObjectType(input.getClassName()));
                            super.visitLdcInsn("/thedarkcolour/futuremc/container/ContainerBarrel.class");
                            super.visitMethodInsn(INVOKEVIRTUAL, "java/lang/Class", "getResource",
                                    "(Ljava/lang/String;)Ljava/net/URL;", false);
                            super.visitJumpInsn(IFNULL, target);
                            changes[0]++;
                        }
                        futureLoaded = false;
                    }
                };
            }
        }, 0);
        if (changes[0] != 1) throw new IllegalStateException("Expected one barrel integration guard");
        Files.write(Path.of(args[1]), output.toByteArray());
    }
}
