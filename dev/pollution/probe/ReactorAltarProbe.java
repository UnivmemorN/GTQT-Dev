package gtqtdev.probe;

import com.mojang.authlib.GameProfile;
import gregtech.api.metatileentity.MetaTileEntity;
import gregtech.api.unification.OreDictUnifier;
import gregtech.api.unification.material.Materials;
import gregtech.api.unification.ore.OrePrefix;
import net.minecraft.block.Block;
import net.minecraft.block.state.IBlockState;
import net.minecraft.entity.EntityLivingBase;
import net.minecraft.inventory.IInventory;
import net.minecraft.item.EnumDyeColor;
import net.minecraft.item.ItemStack;
import net.minecraft.util.EnumFacing;
import net.minecraft.util.EnumHand;
import net.minecraft.util.ResourceLocation;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.World;
import net.minecraft.world.WorldServer;
import net.minecraftforge.common.util.FakePlayer;
import net.minecraftforge.common.util.FakePlayerFactory;
import net.minecraftforge.fml.common.registry.ForgeRegistries;
import net.minecraftforge.oredict.OreDictionary;
import thaumcraft.api.ThaumcraftApi;
import thaumcraft.api.aspects.Aspect;
import thaumcraft.api.blocks.BlocksTC;
import thaumcraft.api.capabilities.IPlayerKnowledge;
import thaumcraft.api.capabilities.ThaumcraftCapabilities;
import thaumcraft.api.crafting.InfusionRecipe;
import thaumcraft.api.items.ItemsTC;
import thaumcraft.common.tiles.crafting.TileInfusionMatrix;
import thaumcraft.common.tiles.essentia.TileJarFillable;

import java.lang.reflect.Method;
import java.util.UUID;

/** The original altar starts by caster interaction and consumes actual jar and pedestal inventories. */
final class ReactorAltarProbe {
    private static final ResourceLocation RECIPE = new ResourceLocation("pollution:magic_fusion_reactor");
    private static final GameProfile OWNER = new GameProfile(
            UUID.fromString("3aabaa50-3d9d-4925-a32d-94a324eb5c0f"), "ReactorAltar");
    private static final int[][] PEDESTALS = {
            {-3, 0}, {3, 0}, {0, -3}, {0, 3}, {-3, -3}, {3, 3}, {-3, 3}, {3, -3}, {-2, 3}, {2, -3}
    };
    private static final int URANIUM = 8;
    private static final int[][] JARS = {{-2, 0}, {2, 0}, {0, -2}, {0, 2}};
    private static final Aspect[] ASPECTS = {Aspect.ENERGY, Aspect.ENTROPY, Aspect.MAGIC, Aspect.VOID};
    private static final int[] AMOUNTS = {250, 250, 128, 64};

    private static BlockPos pos(int x, int y, int z) { return new BlockPos(48 + x, 120 + y, z); }

    private static Object tile(World world, BlockPos at) throws Exception {
        return World.class.getMethod("func_175625_s", BlockPos.class).invoke(world, at);
    }

    private static void place(World world, BlockPos at, Block block) throws Exception {
        IBlockState state = (IBlockState) Block.class.getMethod("func_176223_P").invoke(block);
        World.class.getMethod("func_180501_a", BlockPos.class, IBlockState.class, int.class)
                .invoke(world, at, state, 2);
    }

    private static void build(World world) throws Exception {
        Block stone = ForgeRegistries.BLOCKS.getValue(new ResourceLocation("minecraft:stone"));
        for (int x = -7; x <= 7; x++) {
            for (int z = -6; z <= 6; z++) place(world, pos(x, -3, z), stone);
        }
        for (int x : new int[]{-1, 1}) {
            for (int z : new int[]{-1, 1}) place(world, pos(x, -2, z), BlocksTC.pillarArcane);
        }
        for (int[] p : PEDESTALS) place(world, pos(p[0], -2, p[1]), BlocksTC.pedestalArcane);
        for (int[] p : JARS) place(world, pos(p[0], -2, p[1]), BlocksTC.jarNormal);
        // Matching pairs of sixteen colors provide natural stability for this 692-essentia recipe.
        int pair = 0;
        EnumDyeColor[] colors = EnumDyeColor.values();
        for (int x = 4; x <= 7; x++) {
            for (int z = -6; z <= 6; z++) {
                Block candle = BlocksTC.candles.get(colors[pair++ % colors.length]);
                place(world, pos(x, -2, z), candle);
                place(world, pos(-x, -2, -z), candle);
            }
        }
        place(world, pos(0, -2, 0), BlocksTC.pedestalArcane);
        place(world, pos(0, 0, 0), BlocksTC.infusionMatrix);
        place(world, pos(0, -2, 10), ForgeRegistries.BLOCKS.getValue(new ResourceLocation("minecraft:chest")));
    }

    private static ItemStack get(Object inventory) throws Exception {
        return (ItemStack) IInventory.class.getMethod("func_70301_a", int.class).invoke(inventory, 0);
    }

    private static void set(Object inventory, ItemStack stack) throws Exception {
        IInventory.class.getMethod("func_70299_a", int.class, ItemStack.class).invoke(inventory, 0, stack);
    }

    private static boolean empty(ItemStack stack) throws Exception {
        return (int) ItemStack.class.getMethod("func_190916_E").invoke(stack) == 0;
    }

    private static void require(boolean ok, String detail) {
        if (!ok) throw new IllegalStateException("Reactor altar: " + detail);
    }

    private static void expectProduct(ItemStack stack, ItemStack reactor) {
        require(reactor.serializeNBT().equals(stack.serializeNBT()), "expected " + reactor.serializeNBT()
                + " on altar or in storage, got " + stack.serializeNBT());
    }

    static void run(WorldServer world, String phase) throws Exception {
        boolean reload = "reload".equals(phase);
        require(reload || "create".equals(phase), "unknown phase " + phase);
        if (!reload) build(world);
        BlockPos origin = pos(0, 0, 0);
        TileInfusionMatrix matrix = (TileInfusionMatrix) tile(world, origin);
        require(matrix != null && matrix.validLocation() && !matrix.crafting, "altar structure or state");
        FakePlayer owner = FakePlayerFactory.get(world, OWNER);
        IPlayerKnowledge knowledge = ThaumcraftCapabilities.getKnowledge(owner);
        knowledge.addResearch("INFUSION");
        knowledge.setResearchStage("INFUSION", 2);
        require(knowledge.isResearchKnown("INFUSION@2"), "research missing");
        ItemStack glove = new ItemStack(ItemsTC.casterBasic);
        EntityLivingBase.class.getMethod("func_184611_a", EnumHand.class, ItemStack.class)
                .invoke(owner, EnumHand.MAIN_HAND, glove);

        InfusionRecipe recipe = (InfusionRecipe) ThaumcraftApi.getCraftingRecipes().get(RECIPE);
        require(recipe != null && recipe.getComponents().size() == PEDESTALS.length
                && "INFUSION@2".equals(recipe.getResearch()), "source recipe or research changed");
        MetaTileEntity prototype = (MetaTileEntity) Class.forName(
                "meowmel.pollution.common.metatileentity.PollutionMetaTileEntities")
                .getField("MAGIC_FUSION_REACTOR").get(null);
        ItemStack reactor = (ItemStack) ItemStack.class.getMethod("func_77946_l").invoke(prototype.getStackForm());
        Object centre = tile(world, pos(0, -2, 0));
        Object chest = tile(world, pos(0, -2, 10));
        require(empty(get(chest)), "prior output storage already occupied");
        if (reload) {
            expectProduct(get(centre), reactor);
            set(chest, get(centre));
        } else {
            require(empty(get(centre)), "centre already occupied before first batch");
        }
        set(centre, InfusionCases.one(recipe.getRecipeInput()));

        Object[] stands = new Object[PEDESTALS.length];
        ItemStack uranium = null;
        for (int i = 0; i < stands.length; i++) {
            int[] p = PEDESTALS[i];
            stands[i] = tile(world, pos(p[0], -2, p[1]));
            require(empty(get(stands[i])), "occupied component pedestal " + i);
            if (i == URANIUM) uranium = InfusionCases.compressedUranium235();
            else set(stands[i], InfusionCases.one(recipe.getComponents().get(i)));
        }
        boolean correctIsotope = false;
        for (ItemStack candidate : OreDictionary.getOres("blockUranium235", false)) {
            if (OreDictionary.itemMatches(candidate, uranium, true)) correctIsotope = true;
        }
        require(correctIsotope, "ninth peripheral ingredient is not blockUranium235");
        require(recipe.getAspects().getAspects().length == ASPECTS.length, "unexpected aspect type count");
        TileJarFillable[] jars = new TileJarFillable[JARS.length];
        for (int i = 0; i < jars.length; i++) {
            int[] p = JARS[i];
            jars[i] = (TileJarFillable) tile(world, pos(p[0], -2, p[1]));
            require(jars[i].amount == 0 && recipe.getAspects().getAmount(ASPECTS[i]) == AMOUNTS[i],
                    "jar state or recipe cost changed for " + ASPECTS[i].getTag());
            require(jars[i].addToContainer(ASPECTS[i], AMOUNTS[i]) == 0, "could not fill jar " + i);
        }
        if (!matrix.active) matrix.onCasterRightClick(world, glove, owner, origin, EnumFacing.UP, EnumHand.MAIN_HAND);
        require(matrix.active, "caster did not activate the altar");
        matrix.onCasterRightClick(world, glove, owner, origin, EnumFacing.UP, EnumHand.MAIN_HAND);
        require(!matrix.crafting, "started without uranium-235");
        ItemStack wrongIsotope = OreDictUnifier.get(OrePrefix.block, Materials.Uranium238);
        require(!empty(wrongIsotope), "missing uranium-238 control block");
        set(stands[URANIUM], wrongIsotope);
        matrix.onCasterRightClick(world, glove, owner, origin, EnumFacing.UP, EnumHand.MAIN_HAND);
        require(!matrix.crafting, "started with uranium-238");
        set(stands[URANIUM], uranium);
        matrix.onCasterRightClick(world, glove, owner, origin, EnumFacing.UP, EnumHand.MAIN_HAND);
        require(matrix.crafting, "complete recipe did not start");
        require(matrix.costMult == 1 && matrix.stabilityReplenish >= 1.6F,
                "unexpected altar cost/stabilization " + matrix.costMult + "/" + matrix.stabilityReplenish);

        Method tick = TileInfusionMatrix.class.getMethod("func_73660_a");
        int ticks = 0;
        while (matrix.crafting && ticks < 20000) {
            tick.invoke(matrix);
            ticks++;
        }
        require(!matrix.crafting, "did not finish in " + ticks + " ticks, remaining " + matrix.getAspects().visSize());
        expectProduct(get(centre), reactor);
        for (Object stand : stands) require(empty(get(stand)), "a pedestal ingredient was not consumed");
        for (TileJarFillable jar : jars) require(jar.amount == 0, "unused essentia " + jar.amount);
        if (reload) expectProduct(get(chest), reactor);
        System.out.println("GTQT_REACTOR_ALTAR_OK phase=" + phase + " recipe=" + RECIPE
                + " research=INFUSION@2 central=1 peripheral=10 missingUraniumRejected=true uranium238Rejected=true"
                + " essentia=692 output=1 ticks=" + ticks + " totalOutput=" + (reload ? 2 : 1));
    }
}
