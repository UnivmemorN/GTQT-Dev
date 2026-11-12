import java.nio.file.Files;
import java.nio.file.Path;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassVisitor;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.FieldVisitor;
import org.objectweb.asm.Opcodes;

/** Used only for a positive field-lookup test with the frozen July Core. */
public final class AddTestSunnariumField {
    public static void main(String[] args) throws Exception {
        ClassReader reader = new ClassReader(Files.readAllBytes(Path.of(args[0])));
        if (!reader.getClassName().equals("meowmel/gtqtcore/api/unification/material/GTQTMaterials")) {
            throw new IllegalArgumentException("Expected the July Core material holder");
        }
        ClassWriter writer = new ClassWriter(reader, 0);
        reader.accept(new ClassVisitor(Opcodes.ASM9, writer) {
            @Override
            public FieldVisitor visitField(int access, String name, String desc, String sig, Object value) {
                if (name.equals("Sunnarium")) throw new IllegalStateException("Core already supplies the test field");
                return super.visitField(access, name, desc, sig, value);
            }

            @Override
            public void visitEnd() {
                super.visitField(Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC, "Sunnarium",
                        "Lgregtech/api/unification/material/Material;", null, null).visitEnd();
                super.visitEnd();
            }
        }, 0);
        Files.write(Path.of(args[1]), writer.toByteArray());
    }
}
