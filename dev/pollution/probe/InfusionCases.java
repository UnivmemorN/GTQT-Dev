package gtqtdev.probe;

import gregtech.api.GregTechAPI;
import gregtech.api.recipes.Recipe;
import gregtech.api.recipes.RecipeMap;
import gregtech.api.recipes.RecipeMaps;
import gregtech.api.recipes.ingredients.GTRecipeInput;
import gregtech.api.recipes.properties.RecipeProperty;
import gregtech.api.unification.OreDictUnifier;
import gregtech.api.unification.material.Material;
import gregtech.api.unification.material.Materials;
import gregtech.api.unification.ore.OrePrefix;
import net.minecraft.item.ItemStack;
import net.minecraft.item.crafting.Ingredient;
import net.minecraft.util.ResourceLocation;
import net.minecraftforge.fluids.FluidStack;
import net.minecraftforge.oredict.OreDictionary;
import thaumcraft.api.ThaumcraftApi;
import thaumcraft.api.aspects.Aspect;
import thaumcraft.api.crafting.InfusionRecipe;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Supply original Thaumcraft ingredients to the server test, independently of the GT converter. */
final class InfusionCases {
    private static final String[] IDS = {
            "thaumcraft:elementalsword", "thaumcraft:voidrobehelm", "thaumcraft:voidrobechest",
            "thaumcraft:voidrobelegs", "thaumcraft:primalcrusher", "thaumcraft:causalitycollapser",
            "thaumcraft:voidsiphon", "pollution:magic_circuit_board_iv", "pollution:magic_fusion_reactor"
    };

    static final class Batch {
        final String sourceId;
        final String research;
        final ItemStack[] items;
        final FluidStack[] fluids;
        final ItemStack output;
        final Recipe recipe;

        Batch(String id, String research, List<ItemStack> items, List<FluidStack> fluids, ItemStack output, Recipe recipe) {
            this.sourceId = id;
            this.research = research;
            this.items = items.toArray(new ItemStack[0]);
            this.fluids = fluids.toArray(new FluidStack[0]);
            this.output = output;
            this.recipe = recipe;
        }
    }

    static List<Batch> batches() throws Exception {
        Class<?> maps = Class.forName("meowmel.pollution.api.recipes.PORecipeMaps");
        RecipeMap<?> industrial = (RecipeMap<?>) maps.getField("INDUSTRIAL_INFUSION_RECIPES").get(null);
        Class<?> properties = Class.forName("meowmel.pollution.api.recipes.properties.MagicRecipeProperties");
        RecipeProperty<?> key = (RecipeProperty<?>) properties.getField("THAUMCRAFT_RESEARCH").get(null);
        Map<Aspect, String> materials = expectedMaterials();
        List<Batch> result = new ArrayList<>();
        for (String id : IDS) {
            InfusionRecipe original = (InfusionRecipe) ThaumcraftApi.getCraftingRecipes().get(new ResourceLocation(id));
            require(original != null, id + ": missing source infusion");
            List<ItemStack> items = new ArrayList<>();
            items.add(one(original.getRecipeInput()));
            for (Ingredient component : original.getComponents()) items.add(one(component));
            List<FluidStack> fluids = new ArrayList<>();
            int units = 0;
            for (Aspect aspect : original.getAspects().getAspects()) {
                String name = materials.get(aspect);
                require(name != null, id + ": unrecognized source aspect " + aspect.getTag());
                Material material = GregTechAPI.materialManager.getMaterial("pollution:infused_" + name);
                require(material != null, id + ": missing material " + name);
                int amount = original.getAspects().getAmount(aspect);
                units += amount;
                fluids.add(material.getFluid(144 * amount));
            }

            ItemStack output = (ItemStack) original.recipeOutput;
            List<Recipe> byOutput = new ArrayList<>();
            for (Recipe entry : industrial.getRecipeList()) {
                for (ItemStack product : entry.getOutputs()) {
                    if (OreDictionary.itemMatches(output, product, true)) {
                        byOutput.add(entry);
                        break;
                    }
                }
            }
            require(byOutput.size() == 1, id + ": registered recipes for output " + byOutput.size());
            Recipe recipe = byOutput.get(0);
            ItemStack expected = (ItemStack) ItemStack.class.getMethod("func_77946_l").invoke(output);
            require(recipe.getOutputs().size() == 1, id + ": output count changed " + recipe.getOutputs());
            ItemStack actual = recipe.getOutputs().get(0);
            require(expected.serializeNBT().equals(actual.serializeNBT()), id + ": serialized output changed: source=" +
                    output.serializeNBT() + " sourceCopy=" + expected.serializeNBT() + " industrial=" + actual.serializeNBT());
            require(recipe.getEUt() == 480 && recipe.getDuration() == units * 5, id + ": energy or duration changed");
            require(original.getResearch().equals(recipe.getProperty(key, null)), id + ": research changed");
            require(recipe.getFluidInputs().size() == fluids.size(), id + ": wrong fluid ingredient count");
            for (FluidStack demand : fluids) {
                long exact = recipe.getFluidInputs().stream().filter(in -> in.acceptsFluid(demand) &&
                        in.getAmount() == demand.amount).count();
                require(exact == 1, id + ": wrong amount of " + demand.getFluid().getName());
            }
            int slots = recipe.getInputs().stream().mapToInt(GTRecipeInput::getAmount).sum();
            require(slots == items.size(), id + ": source count " + items.size() + ", imported " + slots);
            if (id.equals("pollution:magic_circuit_board_iv")) {
                require(slots == 29, id + ": expected central board and 28 pedestal items");
            }
            if (id.equals("pollution:magic_fusion_reactor")) {
                require(slots == 11 && units == 692 && "INFUSION@2".equals(original.getResearch()),
                        id + ": expected central frame, ten pedestal items and 692 essentia");
                ItemStack block = compressedUranium235();
                int matches = 0;
                for (int i = 1; i < items.size(); i++) {
                    if (!OreDictionary.itemMatches(items.get(i), block, true)) continue;
                    List<ItemStack> substituted = new ArrayList<>(items);
                    ItemStack otherBlock = OreDictUnifier.get(OrePrefix.block, Materials.Uranium238);
                    require((int) ItemStack.class.getMethod("func_190916_E").invoke(otherBlock) == 1,
                            id + ": missing uranium-238 control block");
                    substituted.set(i, otherBlock);
                    require(!recipe.matches(false, substituted, fluids), id + ": accepted uranium-238 block");
                    for (Material material : Arrays.asList(Materials.Uranium, Materials.Uranium238, Materials.Uranium235)) {
                        substituted.set(i, OreDictUnifier.get(OrePrefix.dust, material, 9));
                        require(!recipe.matches(false, substituted, fluids), id + ": accepted loose dust " + material);
                    }
                    items.set(i, block);
                    matches++;
                }
                require(matches == 1, id + ": expected one compressed uranium-235 pedestal");
            }
            Batch batch = new Batch(id, original.getResearch(), items, fluids, expected, recipe);
            verifyMissingFluidAndItems(batch);
            result.add(batch);
        }
        return result;
    }

    static ItemStack compressedUranium235() throws Exception {
        List<ItemStack> inputs = new ArrayList<>();
        inputs.add(OreDictUnifier.get(OrePrefix.dust, Materials.Uranium235, 9));
        List<FluidStack> dry = Collections.emptyList();
        Recipe recipe = RecipeMaps.COMPRESSOR_RECIPES.findRecipe(32, inputs, dry);
        require(recipe != null && recipe.getEUt() == 2 && recipe.getDuration() == 300
                        && recipe.getOutputs().size() == 1, "missing uranium-235 compression recipe");
        ItemStack product = recipe.getOutputs().get(0);
        require((int) ItemStack.class.getMethod("func_190916_E").invoke(product) == 1
                        && OreDictionary.getOres("blockUranium235", false).stream()
                        .anyMatch(stack -> OreDictionary.itemMatches(stack, product, true)),
                "compressor output does not match blockUranium235");
        require(!recipe.matches(false, Collections.singletonList(OreDictUnifier.get(OrePrefix.dust,
                Materials.Uranium235, 8)), dry), "compressor accepted only eight uranium-235 dusts");
        for (Material wrong : Arrays.asList(Materials.Uranium, Materials.Uranium238)) {
            require(!recipe.matches(false, Collections.singletonList(OreDictUnifier.get(OrePrefix.dust, wrong, 9)), dry),
                    "uranium-235 compressor accepted " + wrong);
        }
        require(recipe.matches(true, inputs, dry)
                        && (int) ItemStack.class.getMethod("func_190916_E").invoke(inputs.get(0)) == 0,
                "compressor did not consume nine uranium-235 dusts");
        return (ItemStack) ItemStack.class.getMethod("func_77946_l").invoke(product);
    }

    static ItemStack one(Ingredient ingredient) throws Exception {
        ItemStack[] examples = (ItemStack[]) Ingredient.class.getMethod("func_193365_a").invoke(ingredient);
        require(examples.length > 0, "empty source ingredient " + ingredient);
        ItemStack stack = (ItemStack) ItemStack.class.getMethod("func_77946_l").invoke(examples[0]);
        ItemStack.class.getMethod("func_190920_e", int.class).invoke(stack, 1);
        if ((int) ItemStack.class.getMethod("func_77960_j").invoke(stack) == OreDictionary.WILDCARD_VALUE) {
            ItemStack.class.getMethod("func_77964_b", int.class).invoke(stack, 0);
        }
        return stack;
    }

    private static void verifyMissingFluidAndItems(Batch batch) {
        List<ItemStack> items = Arrays.asList(batch.items);
        List<FluidStack> fluids = Arrays.asList(batch.fluids);
        require(batch.recipe.matches(false, items, fluids), batch.sourceId + ": complete source ingredients rejected");
        for (int i = 0; i < items.size(); i++) {
            List<ItemStack> shortItems = new ArrayList<>(items);
            shortItems.remove(i);
            require(!batch.recipe.matches(false, shortItems, fluids),
                    batch.sourceId + ": accepted one item less at source position " + i);
        }
        for (int i = 0; i < fluids.size(); i++) {
            List<FluidStack> shortFluids = new ArrayList<>(fluids);
            FluidStack reduced = fluids.get(i).copy();
            reduced.amount--;
            shortFluids.set(i, reduced);
            require(!batch.recipe.matches(false, items, shortFluids),
                    batch.sourceId + ": accepted 1 mB less " + reduced.getFluid().getName());
        }
    }

    private static Map<Aspect, String> expectedMaterials() {
        Map<Aspect, String> map = new HashMap<>();
        map.put(Aspect.AIR, "air");
        map.put(Aspect.MOTION, "motion");
        map.put(Aspect.AVERSION, "weapon");
        map.put(Aspect.METAL, "metal");
        map.put(Aspect.SENSES, "sense");
        map.put(Aspect.PROTECT, "armor");
        map.put(Aspect.ENERGY, "energy");
        map.put(Aspect.ELDRITCH, "alien");
        map.put(Aspect.VOID, "void");
        map.put(Aspect.EARTH, "earth");
        map.put(Aspect.TOOL, "instrument");
        map.put(Aspect.ENTROPY, "entropy");
        map.put(Aspect.DESIRE, "greed");
        map.put(Aspect.FLUX, "taint");
        map.put(Aspect.CRAFT, "craft");
        map.put(Aspect.MAGIC, "magic");
        map.put(Aspect.MECHANISM, "mechanics");
        map.put(Aspect.ORDER, "order");
        map.put(Aspect.AURA, "aura");
        return map;
    }

    private static void require(boolean ok, String msg) {
        if (!ok) throw new IllegalStateException("Infusion acceptance: " + msg);
    }
}
