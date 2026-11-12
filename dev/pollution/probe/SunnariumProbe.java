package gtqtdev.probe;

import gregtech.api.GregTechAPI;
import gregtech.api.recipes.Recipe;
import gregtech.api.recipes.RecipeMap;
import gregtech.api.recipes.ingredients.GTRecipeInput;
import gregtech.api.unification.Element;
import gregtech.api.unification.OreDictUnifier;
import gregtech.api.unification.material.Material;
import gregtech.api.unification.material.event.MaterialEvent;
import gregtech.api.unification.material.info.MaterialIconSet;
import gregtech.api.unification.ore.OrePrefix;
import net.minecraft.item.ItemStack;
import net.minecraft.util.ResourceLocation;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.common.event.FMLPreInitializationEvent;
import net.minecraftforge.fml.common.event.FMLServerStartingEvent;
import net.minecraftforge.fml.common.eventhandler.EventPriority;
import net.minecraftforge.fml.common.eventhandler.SubscribeEvent;
import net.minecraftforge.oredict.OreDictionary;

import java.io.FileReader;
import java.io.IOException;
import java.util.Properties;

/** Dedicated-server acceptance fixture, never part of the player profile. */
@Mod(modid = "gtqtcompatprobe", version = "1", acceptableRemoteVersions = "*")
public final class SunnariumProbe {
    private static final String WORLD_RULE = "gtqtCompatWorldMarker";
    private static final Properties options = new Properties();

    @Mod.EventHandler
    public void configure(FMLPreInitializationEvent event) throws IOException {
        try (FileReader in = new FileReader("gtqt-probe.properties")) {
            options.load(in);
        }
    }

    @Mod.EventBusSubscriber(modid = "gtqtcompatprobe")
    public static final class Supplier {
        private static Material fixture;

        @SubscribeEvent(priority = EventPriority.HIGH)
        public static void register(MaterialEvent event) throws Exception {
            // Material registration can precede this mod's own FML pre-init.
            Properties settings = new Properties();
            try (FileReader in = new FileReader("gtqt-probe.properties")) {
                settings.load(in);
            }
            String mode = settings.getProperty("mode");
            if (!"fallback".equals(mode)) {
                boolean field = "core-field".equals(mode);
                String name = field ? "field_fixture_sun" : "sunnarium";
                fixture = new Material.Builder(30000, new ResourceLocation("gtqtcore", name))
                        .dust().color(0x119933).build();
                if (field) {
                    Class.forName("meowmel.gtqtcore.api.unification.material.GTQTMaterials")
                            .getField("Sunnarium").set(null, fixture);
                }
            }
        }
    }

    private static void require(boolean ok, String what) {
        if (!ok) throw new IllegalStateException("GTQT compatibility probe failed: " + what);
    }

    @Mod.EventHandler
    public void verify(FMLServerStartingEvent event) throws Exception {
        Material material = (Material) Class.forName("meowmel.pollution.api.unification.PollutionMaterials")
                .getField("Sunnarium").get(null);
        long count = GregTechAPI.materialManager.getRegisteredMaterials().stream()
                .filter(m -> "sunnarium".equals(m.getName())).count();
        String mode = options.getProperty("mode");
        require(material != null && count == ("core-field".equals(mode) ? 0 : 1), "unexpected Sunnarium count " + count);
        require(material == GregTechAPI.materialManager.getMaterial(material.getRegistryName()), "registry identity");
        if (!"fallback".equals(mode)) {
            require(material == Supplier.fixture && material.getMaterialRGB() == 0x119933, "supplier identity");
        } else {
            require("pollution:sunnarium".equals(material.getRegistryName()) && material.getId() == 14, "fallback ID");
            Element e = material.getElement();
            require(e != null && "Su".equals(e.symbol) && "Sunnarium".equals(e.name) && e.protons == 1 &&
                    e.neutrons == 8 && e.halfLifeSeconds == -1 && e.decayTo == null && !e.isIsotope, "fallback element");
            require(material.getMaterialRGB() == 0xFAF20E && material.getMaterialIconSet() == MaterialIconSet.SHINY &&
                    material.getFluid() != null, "fallback material properties");
        }

        ItemStack dust = OreDictUnifier.get(OrePrefix.dust, material);
        require(OreDictUnifier.getMaterial(dust) != null && OreDictUnifier.getMaterial(dust).material == material,
                "ore dictionary dust");
        Class<?> maps = Class.forName("meowmel.pollution.api.recipes.PORecipeMaps");
        RecipeMap<?> reactor = (RecipeMap<?>) maps.getField("MAGIC_CHEMICAL_REACTOR_RECIPES").get(null);
        long reactorMatches = reactor.getRecipeList().stream()
                .filter(r -> r.getEUt() == 480 && r.getDuration() == 200)
                .filter(r -> r.getOutputs().stream().anyMatch(s -> OreDictionary.itemMatches(s, dust, false))).count();
        require(reactorMatches == 1, "magic reactor Sunnarium recipe, found " + reactorMatches);
        Object card = Class.forName("meowmel.pollution.common.items.PollutionMetaItems").getField("TAROT_THE_SUN").get(null);
        ItemStack sun = (ItemStack) card.getClass().getMethod("getStackForm").invoke(card);
        RecipeMap<?> assembler = (RecipeMap<?>) maps.getField("MAGIC_ASSEMBLER_RECIPES").get(null);
        int tarotMatches = 0;
        for (Recipe recipe : assembler.getRecipeList()) {
            if (recipe.getDuration() != 200 || recipe.getOutputs().stream().noneMatch(s -> OreDictionary.itemMatches(s, sun, false))) continue;
            for (GTRecipeInput input : recipe.getInputs()) {
                if (input.getAmount() == 2 && input.acceptsStack(dust)) {
                    tarotMatches++;
                    break;
                }
            }
        }
        require(tarotMatches == 1, "Sun tarot recipe using two Sunnarium dust, found " + tarotMatches);

        // Invoke vanilla's stable_39 SRG names so the small acceptance fixture runs in production Forge.
        Object server = event.getServer();
        Object overworld = server.getClass().getMethod("func_71218_a", int.class).invoke(server, 0);
        Object rules = overworld.getClass().getMethod("func_82736_K").invoke(overworld);
        String phase = options.getProperty("phase");
        String marker = options.getProperty("marker");
        if ("create".equals(phase)) {
            require(!(Boolean) rules.getClass().getMethod("func_82765_e", String.class).invoke(rules, WORLD_RULE), "world must be new");
            rules.getClass().getMethod("func_82764_b", String.class, String.class).invoke(rules, WORLD_RULE, marker);
        } else {
            require("reload".equals(phase), "unknown phase");
        }
        require(marker.equals(rules.getClass().getMethod("func_82767_a", String.class).invoke(rules, WORLD_RULE)), "overworld marker");
        boolean processing = Boolean.parseBoolean(options.getProperty("processing"));
        boolean legacy = Boolean.parseBoolean(options.getProperty("legacyInfusion"));
        if (Boolean.parseBoolean(options.getProperty("reactorAltar"))) {
            ReactorAltarProbe.run((net.minecraft.world.WorldServer) overworld, phase);
        }
        if (processing || legacy) {
            if (processing) ImportGuardProbe.verify();
            ProcessingProbe.run((net.minecraft.world.WorldServer) overworld,
                    (net.minecraft.server.management.PlayerList) server.getClass().getMethod("func_184103_al").invoke(server),
                    phase, legacy);
        }
        System.out.printf("GTQT_PROBE_OK phase=%s marker=%s material=%s id=%d reactor=%d tarot=%d%n",
                phase, marker, material.getRegistryName(), material.getId(), reactorMatches, tarotMatches);
    }
}
