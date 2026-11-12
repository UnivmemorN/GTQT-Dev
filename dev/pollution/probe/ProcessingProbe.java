package gtqtdev.probe;

import com.mojang.authlib.GameProfile;
import gregtech.api.capability.IEnergyContainer;
import gregtech.api.capability.impl.MultiblockRecipeLogic;
import gregtech.api.metatileentity.MetaTileEntity;
import gregtech.api.metatileentity.interfaces.IGregTechTileEntity;
import gregtech.api.metatileentity.multiblock.MultiblockAbility;
import gregtech.api.metatileentity.multiblock.RecipeMapMultiblockController;
import gregtech.api.pattern.StructureOperationRequest;
import gregtech.api.pattern.StructureOrientation;
import gregtech.api.recipes.Recipe;
import gregtech.api.recipes.logic.CrossRecipeParallelScheduler;
import gregtech.api.unification.material.Material;
import gregtech.api.util.GTTransferUtils;
import gregtech.api.util.GTUtility;
import net.minecraft.block.Block;
import net.minecraft.block.state.IBlockState;
import net.minecraft.entity.player.EntityPlayerMP;
import net.minecraft.item.ItemStack;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.server.management.PlayerList;
import net.minecraft.util.EnumFacing;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.World;
import net.minecraft.world.WorldServer;
import net.minecraftforge.common.util.FakePlayer;
import net.minecraftforge.common.util.FakePlayerFactory;
import net.minecraftforge.fluids.FluidStack;
import net.minecraftforge.fluids.IFluidTank;
import net.minecraftforge.items.IItemHandler;
import thaumcraft.api.capabilities.IPlayerKnowledge;
import thaumcraft.api.capabilities.ThaumcraftCapabilities;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/** Exercises the production controller in a persisted dedicated-server world. */
final class ProcessingProbe {
    private static final String PO_TILES = "meowmel.pollution.common.metatileentity.PollutionMetaTileEntities";
    private static final String GT_TILES = "gregtech.common.metatileentities.MetaTileEntities";
    private static final BlockPos ORIGIN = new BlockPos(0, 120, 0);
    private static final GameProfile OWNER = new GameProfile(
            UUID.fromString("f09e3d96-8466-4cc8-98ae-7222468230ea"), "InfusionProbe");

    // The fixture is compiled against the development Minecraft JAR and executed in SRG Forge.
    private static final Method SET_STATE = method(World.class, "func_180501_a", BlockPos.class, IBlockState.class, int.class);
    private static final Method STATE = method(World.class, "func_180495_p", BlockPos.class);
    private static final Method TILE = method(World.class, "func_175625_s", BlockPos.class);
    private static final Method DEFAULT_STATE = method(Block.class, "func_176223_P");
    private static final Method COUNT = method(ItemStack.class, "func_190916_E");
    private static final Method COPY = method(ItemStack.class, "func_77946_l");
    private static final Method SAME_ITEM = method(ItemStack.class, "func_77969_a", ItemStack.class);
    private static final Method REMOVE_TAG = method(NBTTagCompound.class, "func_82580_o", String.class);

    private static Method method(Class<?> owner, String name, Class<?>... parameters) {
        try {
            return owner.getMethod(name, parameters);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException(name, e);
        }
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalStateException("Infusion processing: " + message);
    }

    private static int count(ItemStack stack) throws ReflectiveOperationException {
        return (int) COUNT.invoke(stack);
    }

    private static int inventoryCount(IItemHandler inventory, ItemStack target) throws ReflectiveOperationException {
        int total = 0;
        for (int slot = 0; slot < inventory.getSlots(); slot++) {
            ItemStack stack = inventory.getStackInSlot(slot);
            if (target == null) {
                total += count(stack);
            } else if ((boolean) SAME_ITEM.invoke(target, stack)) {
                NBTTagCompound expected = target.serializeNBT();
                NBTTagCompound actual = stack.serializeNBT();
                REMOVE_TAG.invoke(expected, "Count");
                REMOVE_TAG.invoke(actual, "Count");
                if (expected.equals(actual)) total += count(stack);
            }
        }
        return total;
    }

    private static MetaTileEntity place(World world, BlockPos pos, MetaTileEntity prototype) throws Exception {
        SET_STATE.invoke(world, pos, DEFAULT_STATE.invoke(prototype.getBlock()), 2);
        IGregTechTileEntity holder = (IGregTechTileEntity) TILE.invoke(world, pos);
        require(holder != null, "no holder for " + prototype.metaTileEntityId + " at " + pos);
        return holder.setMetaTileEntity(prototype);
    }

    private static MetaTileEntity hatch(String owner, String field, int tier) throws ReflectiveOperationException {
        return ((MetaTileEntity[]) Class.forName(owner).getField(field).get(null))[tier];
    }

    private static void build(World world, RecipeMapMultiblockController machine, FakePlayer player, boolean legacy)
            throws Exception {
        Object capabilities = player.getClass().getField("field_71075_bZ").get(player);
        capabilities.getClass().getField("field_75098_d").setBoolean(capabilities, true);
        machine.getOrCreateStructureRuntime().creativeBuildAllPieces(StructureOperationRequest.creativeBuild(
                player, machine, StructureOrientation.fromController(machine), Collections.emptyMap()));

        // Replace optional casing positions with the production buses, hatches and energy input.
        Method casingState = machine.getClass().getDeclaredMethod("getCasingState");
        casingState.setAccessible(true);
        IBlockState casing = (IBlockState) casingState.invoke(null);
        List<BlockPos> casings = new ArrayList<>();
        boolean hasMagicHatch = false;
        for (int x = -30; x <= 30; x++) {
            for (int z = -30; z <= 30; z++) {
                for (int y = 118; y <= 122; y++) {
                    BlockPos pos = new BlockPos(x, y, z);
                    if (STATE.invoke(world, pos) == casing) casings.add(pos);
                    else if (GTUtility.getMetaTileEntity(world, pos) instanceof IFluidTank) {
                        MetaTileEntity part = GTUtility.getMetaTileEntity(world, pos);
                        if (part.metaTileEntityId.toString().startsWith("pollution:infused_fluid_hatch.")) {
                            hasMagicHatch = true;
                        }
                    }
                }
            }
        }
        List<MetaTileEntity> parts = new ArrayList<>();
        parts.add(hatch(GT_TILES, "ITEM_IMPORT_BUS", 5));
        parts.add(hatch(GT_TILES, "ITEM_EXPORT_BUS", 5));
        parts.add(hatch(GT_TILES, "ENERGY_INPUT_HATCH", 5));
        for (int i = 0; i < 10; i++) parts.add(hatch(GT_TILES, "FLUID_IMPORT_HATCH", 4));
        if (!hasMagicHatch) parts.add(hatch(PO_TILES, "INFUSED_FLUID_HATCH", 4));
        if (legacy) {
            // A naturally ticking export bus can push the saved output blockers into a neighboring import bus.
            // Give each item bus a free exterior face and reserve its neighboring blocks before placing other hatches.
            Method offset = method(BlockPos.class, "func_177972_a", EnumFacing.class);
            Method air = method(World.class, "func_175623_d", BlockPos.class);
            for (MetaTileEntity bus : new ArrayList<>(parts.subList(0, 2))) {
                boolean placed = false;
                Set<BlockPos> reserved = new HashSet<>();
                for (BlockPos pos : casings) {
                    EnumFacing outlet = null;
                    reserved.clear();
                    reserved.add(pos);
                    boolean hasNeighbor = false;
                    for (EnumFacing face : EnumFacing.values()) {
                        BlockPos neighbor = (BlockPos) offset.invoke(pos, face);
                        reserved.add(neighbor);
                        if (GTUtility.getMetaTileEntity(world, neighbor) != null) hasNeighbor = true;
                        if ((boolean) air.invoke(world, neighbor)) outlet = face;
                    }
                    if (hasNeighbor || outlet == null) continue;
                    place(world, pos, bus).setFrontFacing(outlet);
                    placed = true;
                    break;
                }
                require(placed, "no isolated outside face for legacy item bus " + bus.metaTileEntityId);
                casings.removeAll(reserved);
            }
            parts.subList(0, 2).clear();
        }
        require(casings.size() >= parts.size(), "creative build produced only " + casings.size() + " casings");
        for (int i = 0; i < parts.size(); i++) place(world, casings.get(i), parts.get(i));
        machine.markDirty();
    }

    @SuppressWarnings("unchecked")
    static void run(WorldServer world, PlayerList list, String phase, boolean legacy) throws Exception {
        FakePlayer owner = FakePlayerFactory.get(world, OWNER);
        Field online = PlayerList.class.getDeclaredField("field_177454_f");
        online.setAccessible(true);
        Map<UUID, EntityPlayerMP> players = (Map<UUID, EntityPlayerMP>) online.get(list);
        require(!players.containsKey(OWNER.getId()), "test owner UUID already logged in");
        players.put(OWNER.getId(), owner);
        try {
            // Read the whole structure's chunks before attempting the production match on reload.
            for (int x = -32; x <= 32; x += 16) {
                for (int z = -32; z <= 32; z += 16) STATE.invoke(world, new BlockPos(x, 120, z));
            }
            RecipeMapMultiblockController machine;
            if ("create".equals(phase)) {
                require(GTUtility.getMetaTileEntity(world, ORIGIN) == null, "expected fresh world");
                MetaTileEntity prototype = (MetaTileEntity) Class.forName(PO_TILES).getField("INDUSTRIAL_INFUSION").get(null);
                machine = (RecipeMapMultiblockController) place(world, ORIGIN, prototype);
                machine.onPlacement(owner);
                build(world, machine, owner, legacy);
            } else {
                machine = (RecipeMapMultiblockController) GTUtility.getMetaTileEntity(world, ORIGIN);
            }
            require(machine != null && OWNER.getId().equals(machine.getOwnerGT()), "missing persisted controller or owner");
            machine.checkStructurePattern();
            require(machine.isStructureFormed(), "actual pattern failed: " + machine.getLastStructureError()
                    + " / " + machine.getMissingStructureAbilities());
            MultiblockAbility<IFluidTank> ability = (MultiblockAbility<IFluidTank>) Class.forName(
                    "meowmel.pollution.api.metatileentity.POMultiblockAbility").getField("INFUSED_FLUID_HATCH").get(null);
            List<IFluidTank> magic = machine.getAbilities(ability);
            require(magic.size() == 1, "missing infused-fluid hatch");
            Material infusedMagic = (Material) Class.forName("meowmel.pollution.api.unification.PollutionMaterials")
                    .getField("InfusedMagic").get(null);
            if (legacy) {
                LegacyInfusionProbe.exercise(machine, magic.get(0), infusedMagic, phase);
                return;
            }
            List<InfusionCases.Batch> batches = InfusionCases.batches();
            IPlayerKnowledge knowledge = ThaumcraftCapabilities.getKnowledge(owner);
            for (InfusionCases.Batch batch : batches) {
                int priorCrafts = "pollution:magic_circuit_board_iv".equals(batch.sourceId) ? 3 : 1;
                int previous = "reload".equals(phase) ? priorCrafts * count(batch.output) : 0;
                require(inventoryCount(machine.getOutputInventory(), batch.output) == previous,
                        "incorrect persisted output before " + phase + " " + batch.sourceId);
            }
            for (InfusionCases.Batch batch : batches) {
                if (!batch.research.isEmpty()) {
                    String[] stage = batch.research.split("@", 2);
                    knowledge.addResearch(stage[0]);
                    if (stage.length == 2) knowledge.setResearchStage(stage[0], Integer.parseInt(stage[1]));
                    require(knowledge.isResearchKnown(batch.research), "cannot grant research " + batch.research);
                }
                craft(machine, magic.get(0), infusedMagic, batch, phase, 1);
                if ("pollution:magic_circuit_board_iv".equals(batch.sourceId)) {
                    craft(machine, magic.get(0), infusedMagic, batch, phase, 2);
                }
            }
        } finally {
            players.remove(OWNER.getId());
        }
    }

    private static void craft(RecipeMapMultiblockController machine, IFluidTank magic, Material infusedMagic,
                              InfusionCases.Batch batch, String phase, int copies) throws Exception {
        int fluidTotal = 0;
        int itemTotal = 0;
        require(inventoryCount(machine.getInputInventory(), null) == 0, "input bus already contains items");
        for (int i = 0; i < copies; i++) {
            for (ItemStack stack : batch.items) {
                itemTotal += count(stack);
                // A bus can retain its inserted stack and grow it when a later pedestal stacks with it.
                require(count(GTTransferUtils.insertItem(machine.getInputInventory(), (ItemStack) COPY.invoke(stack), false)) == 0,
                        "input bus rejected " + stack);
            }
            for (FluidStack cost : batch.fluids) {
                require(machine.getInputFluidInventory().fill(cost.copy(), true) == cost.amount, "input hatch rejected " + cost);
                fluidTotal += cost.amount;
            }
        }
        require(itemTotal == batch.items.length * copies && inventoryCount(machine.getInputInventory(), null) == itemTotal,
                "wrong input count staged for " + batch.sourceId + ": " + itemTotal);
        require(batch.recipe.matches(false, machine.getInputInventory(), machine.getInputFluidInventory()),
                "source ingredients don't match " + batch.sourceId);
        magic.fill(infusedMagic.getFluid(magic.getCapacity()), true);
        int magicBefore = magic.getFluidAmount();
        int outputBefore = inventoryCount(machine.getOutputInventory(), batch.output);
        IEnergyContainer energy = machine.getEnergyContainer();
        energy.addEnergy(energy.getEnergyCanBeInserted());
        MultiblockRecipeLogic work = machine.getRecipeMapWorkable();
        Recipe lookedUp = work.getRecipeMap().findRecipe(work.getMaxVoltage(),
                machine.getInputInventory(), machine.getInputFluidInventory());
        require(lookedUp == batch.recipe, batch.sourceId + " real recipe lookup returned " + lookedUp);
        require(machine.checkRecipe(batch.recipe, false) && work.checkRecipe(batch.recipe),
                batch.sourceId + " owner/research/magic check failed: owner=" + machine.getOwnerGT()
                        + " research=" + batch.research + " infused=" + magicBefore);
        work.forceRecipeRecheck();
        CrossRecipeParallelScheduler scheduler = work.getCrossRecipeScheduler();
        boolean inSlot = scheduler != null && scheduler.getActiveSlots().stream()
                .anyMatch(slot -> slot.getSourceRecipe() == batch.recipe);
        require(work.isActive() && (inSlot || work.getPreviousRecipe() == batch.recipe),
                "did not start " + batch.sourceId + ": " + work.getWhyFailed() + " voltage=" + work.getMaxVoltage()
                        + " energy=" + energy.getEnergyStored() + " progress=" + work.getProgress()
                        + " parallel=" + work.getParallelLimit() + " scheduler=" + work.usesParallelScheduler()
                        + " activeSlots=" + (scheduler == null ? 0 : scheduler.getActiveSlotCount())
                        + " previous=" + work.getPreviousRecipe() + " active=" + work.isActive());
        int actualParallel = work.getParallelRecipesPerformed();
        require(copies == 1 || actualParallel == copies,
                batch.sourceId + " expected " + copies + " simultaneous runs; performed " + actualParallel);
        require(inventoryCount(machine.getInputInventory(), null) == 0, batch.sourceId + " retained "
                + inventoryCount(machine.getInputInventory(), null) + " / " + itemTotal + " items at parallel " + actualParallel);
        for (int i = 0; i < machine.getInputFluidInventory().getTanks(); i++) {
            require(machine.getInputFluidInventory().getTankAt(i).getFluidAmount() == 0,
                    batch.sourceId + " undercharged an aspect");
        }
        long spent = 0;
        int ticks = 0;
        int quantity = copies * count(batch.output);
        int expectedOutput = outputBefore + quantity;
        int pauseStart = 0;
        int pauseEnd = 0;
        int stalledTicks = 0;
        if (copies > 1) {
            // Let the official work logic advance, then interrupt only the dedicated magic hatch.
            for (int i = 0; i < 4; i++) {
                energy.addEnergy(energy.getEnergyCanBeInserted());
                long before = energy.getEnergyStored();
                work.updateWorkable();
                spent += before - energy.getEnergyStored();
                ticks++;
            }
            pauseStart = work.getProgress();
            require(pauseStart > 1, "batch never advanced before its magic supply was cut");
            FluidStack withheld = magic.drain(magic.getCapacity(), true);
            require(withheld != null && magic.getFluidAmount() == 0, "failed to cut the magic supply");
            long energyAtCut = energy.getEnergyStored();
            for (int i = 0; i < 12; i++) {
                work.updateWorkable();
                stalledTicks++;
            }
            pauseEnd = work.getProgress();
            require(energy.getEnergyStored() == energyAtCut && pauseEnd <= pauseStart
                            && inventoryCount(machine.getOutputInventory(), batch.output) == outputBefore,
                    "batch consumed EU, advanced or emitted output without infused magic");
            require(magic.fill(withheld, true) == withheld.amount, "failed to reconnect the magic supply");
        }
        while (inventoryCount(machine.getOutputInventory(), batch.output) != expectedOutput
                && ticks < batch.recipe.getDuration() + 40) {
            energy.addEnergy(energy.getEnergyCanBeInserted());
            long before = energy.getEnergyStored();
            work.updateWorkable();
            spent += before - energy.getEnergyStored();
            ticks++;
        }
        require(inventoryCount(machine.getOutputInventory(), batch.output) == expectedOutput && spent > 0
                        && magic.getFluidAmount() < magicBefore,
                batch.sourceId + " failed to deliver output: progress=" + work.getProgress() + "/" + work.getMaxProgress()
                        + " EU=" + spent + " infused=" + (magicBefore - magic.getFluidAmount())
                        + " activeScheduler=" + inSlot);
        System.out.printf("%s phase=%s recipe=%s output=%s quantity=%d ticks=%d eu=%d items=%d aspectsMb=%d infusedMb=%d totalInOutput=%d parallel=%d stalledTicks=%d cutProgress=%d stalledProgress=%d%n",
                copies == 1 ? "GTQT_PROCESS_OK" : "GTQT_INFUSION_BATCH_OK", phase, batch.sourceId, batch.output, quantity,
                ticks, spent, itemTotal, fluidTotal, magicBefore - magic.getFluidAmount(), expectedOutput,
                actualParallel, stalledTicks, pauseStart, pauseEnd);
    }
}
