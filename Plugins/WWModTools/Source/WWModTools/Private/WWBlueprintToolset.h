#pragma once

#include "CoreMinimal.h"
#include "ToolsetRegistry/ToolsetDefinition.h"

#include "WWBlueprintToolset.generated.h"

/**
 * Tools for editing Blueprint function graphs from generated T3D (the text the editor copies and pastes).
 *
 * BlueprintPath is a package path such as "/Game/Mods/FreightDock/BP_MapLoad".
 * Pin types are FEdGraphPinType text, e.g. (PinCategory="int",ContainerType=Set) or
 * (PinCategory="object",PinSubCategoryObject="/Script/CoreUObject.Class'/Script/Engine.Actor'").
 * Edits are not saved until CompileAndSave.
 */
UCLASS(BlueprintType)
class UWWBlueprintToolset : public UToolsetDefinition
{
	GENERATED_BODY()
public:

	/**
	 * Lists a Blueprint's graphs (functions, macros, event graphs) and member variables with their pin types.
	 * @param BlueprintPath Package path of the Blueprint.
	 * @return One line per graph and per variable.
	 */
	UFUNCTION(meta = (AICallable), Category = "WWBlueprintToolset")
	static FString ListGraphs(const FString& BlueprintPath);

	/**
	 * Adds member variables, or updates the type and default value of ones that already exist.
	 * @param BlueprintPath Package path of the Blueprint.
	 * @param VariablesFile Absolute path of a JSON file: [{"name": "...", "type": "<pin type text>", "default": "..."}].
	 * @return One line per variable: added, updated, unchanged, or the error.
	 */
	UFUNCTION(meta = (AICallable), Category = "WWBlueprintToolset")
	static FString EnsureVariables(const FString& BlueprintPath, const FString& VariablesFile);

	/**
	 * Creates or replaces a function graph from a spec file.
	 * The spec is JSON: {"function", "pure", "t3d" (file relative to the spec, or null for the signature only),
	 * "inputs"/"outputs"/"locals": [{"name", "type", "default"}], "entry": [node, pin],
	 * "returns": [[node, pin], ...], "returnValues": [[node, pin, output], ...]}.
	 * Nodes are found by their comment (the generator labels every node). The signature is applied first, then the
	 * old body is removed and the T3D is pasted and wired to the entry and return nodes.
	 * Define every function's signature (SignatureOnly = true) before importing bodies that call each other.
	 * @param BlueprintPath Package path of the Blueprint.
	 * @param SpecFile Absolute path of the spec JSON.
	 * @param SignatureOnly Only create the function and set its inputs, outputs, locals and purity.
	 * @return What was done, including any labels or pins that could not be found or connected.
	 */
	UFUNCTION(meta = (AICallable), Category = "WWBlueprintToolset")
	static FString ImportFunction(const FString& BlueprintPath, const FString& SpecFile, bool SignatureOnly);

	/**
	 * Deletes a function graph.
	 * @param BlueprintPath Package path of the Blueprint.
	 * @param FunctionName The function to remove.
	 * @return Confirmation, or an error if there is no such function.
	 */
	UFUNCTION(meta = (AICallable), Category = "WWBlueprintToolset")
	static FString RemoveFunction(const FString& BlueprintPath, const FString& FunctionName);

	/**
	 * Exports every node of a graph as T3D.
	 * @param BlueprintPath Package path of the Blueprint.
	 * @param GraphName Function, macro or event graph name (e.g. "EventGraph").
	 * @param OutFile Absolute path to write the T3D to; when empty the T3D is returned instead.
	 * @return The T3D, or a summary when written to OutFile.
	 */
	UFUNCTION(meta = (AICallable), Category = "WWBlueprintToolset")
	static FString ExportGraph(const FString& BlueprintPath, const FString& GraphName, const FString& OutFile);

	/**
	 * Compiles a Blueprint and optionally saves its package.
	 * @param BlueprintPath Package path of the Blueprint.
	 * @param Save Save the package after compiling (also when there are errors, so work is not lost).
	 * @return Error and warning counts followed by each compiler message.
	 */
	UFUNCTION(meta = (AICallable), Category = "WWBlueprintToolset")
	static FString CompileAndSave(const FString& BlueprintPath, bool Save);
};
